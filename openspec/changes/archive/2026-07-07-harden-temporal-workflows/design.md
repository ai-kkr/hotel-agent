## Context

Воркфлоу `BookingWorkflow` (один на бронирование, `workflow_id = booking_id`) — «спина» всего pipeline. Он детерминирован, сайд-эффекты вынесены в активности `ConciergeActivities`, на границе — pydantic-DTO. Слои изолированы, идемпотентность `send_email` заложена через `idempotency_key`. Это хорошая база.

Но это всё «как стартовать», а не «как жить 30 дней». Четыре проблемы:

1. **Регистрация падает.** `Worker(activities=[activities])` передаёт инстанс; temporalio 1.30.0 не открывает методы инстанса автоматически, а вызывает `must_from_callable` для каждого элемента списка → `TypeError: Activity <unknown> missing attributes`. Это никогда не ловилось, потому что E2E-тест (`test_workflow_integration.py`) спрятан за `KKR_E2E_TEMPORAL=1` и использует ту же неправильную регистрацию.
2. **Всё дефолтное.** Все активности — дефолтный infinite retry + `start_to_close_timeout=120s`. Для LLM (`extract`, `agent_turn`) это риск «вечного» 120-секундного цикла и безлимитных трат при дауне провайдера.
3. **History растёт без границ.** Воркфлоу long-lived (`_await_reactivation` ждёт до 30 дней, D11). Каждая итерация переговоров добавляет события; без Continue-As-New история растёт вплоть до серверного лимита (~50k событий / ~50MB), после чего воркфлоу блокируется.
4. **Нет версионирования.** Любое изменение логики `run()`/`_negotiate()` ломает replay уже запущенных long-lived воркфлоу → non-determinism errors.

Смежный нюанс: таймауты 14/30 дней захардкожены в теле воркфлоу (`_await_followup`, `_await_reactivation`), а не в параметрах `run()`.

## Goals / Non-Goals

**Goals:**
- Воркер стартует против реального Temporal без ошибок регистрации.
- Retry/timeout-политики детерминированы и ограничены; LLM-активности не уйдут в бесконечный retry.
- Event History ограничена через Continue-As-New — воркфлоу может жить недели без роста истории.
- Введён `workflow.patcher`-маркер, документирующий безопасный путь изменения логики работающих воркфлоу.
- Таймауты ожидания вынесены в параметры/настройки.
- E2E-покрытие корректной регистрации, bounded-retry и continue-as-new.

**Non-Goals:**
- Перепроектирование логики переговоров (интенты, topic-resolution) — она остаётся как есть.
- Observability-стек (interceptors/метрики) — отдельно.
- Мульти-тенантный Task Queue Fairness — для v1 один task queue.
- Миграция существующих запущенных воркфлоу — в проде воркфлоу ещё нет (v1), поэтому стратегия «deploy fresh».

## Decisions

### D1. Регистрация через явный список bound-методов
Передавать `activities=[instance.extract, instance.discover_contact, ...]`, а не `activities=[instance]`. Альтернатива — единый helper `activity_methods(instance)`, собирающий методы по атрибуту `__temporal_activity_definition`, но это магия отражения; явный список самодокументирован и ловит опечатки на старте. Методов 8 — явный список приемлем.

### D2. Retry-политики по классу активности
Две группы политик (через константы в `workflow.py`):

| Группа | Активности | Policy |
|---|---|---|
| LLM | `extract`, `agent_turn` | `max_attempts=3`, backoff `initial=2s, max=30s`, `non_retryable_error_types` для невосстановимых ошибок модели |
| Сайд-эффекты (идемпотентные) | `send_email`, `relay_to_client`, `update_booking_state`, `build_report` | `max_attempts=5`, backoff `initial=5s, max=60s` |
| Discovery | `discover_contact` | `max_attempts=3` (внешний web-поиск, дорогой) |

Передаются через `retry=` в `execute_activity`. Альтернатива — вынести в настройки, но это подробности выполнения, а не среды; оставляем константами с возможностью оверрайда через `Settings` (D6).

Таймаут: поднять `start_to_close_timeout` для LLM до `180s` (реалистичный потолок cold-LLM); оставить `120s` для прочих.

### D3. Continue-As-New как счётчик туров
Вместо «по размеру истории» (нет простого API из воркфлоу) — счётчик «туров переговоров» как **instance-local** атрибут воркфлоу (`self._negotiation_runs`). После достижения `workflow_continue_as_new_threshold` (по умолчанию 5) воркфлоу вызывает `workflow.continue_as_new(args=[resume, ...])`, передавая `ResumeInput` (накопленное `BookingState` + текущий триггер + необслуженные сигналы). Счётчик хранится на экземпляре, а не в `BookingState`: новый run = новый экземпляр воркфлоу, поэтому счётчик сбрасывается автоматически; в `BookingState` он пережил бы handoff и порог сработал бы сразу → бесконечный continue-as-new.

API: в установленном temporalio 1.30.0 доступен `workflow.patched(id)` (не `patcher`/`patch`) — контракт D4 опирается на него.

Состояние, передаваемое в continue-as-new: `BookingState` + текущий `trigger_kind/body/subject` + необслуженные элементы очередей сигналов (как стартовый аргумент-«mailbox»). Это сохраняет семантику: новый run продолжает с того же места.

Альтернатива — не делать continue-as-new, а ограничить lifetime `workflow_execution_timeout`. Отвергнуто: таймаут убивает воркфлоу, а не сбрасывает историю; теряем long-lived-семантику D11.

### D4. Версионирование через `workflow.patched`
Сейчас воркфлоу v1; менять логику ещё не нужно. Но вводим правило: **любое** изменение структуры команд воркфлоу (новая/удалённая активность, изменение порядка `_negotiate`, новые ветки) обязано оборачиваться в `workflow.patched("<change-id>")` (API доступный в temporalio 1.30.0). Документируем это в `workflow.py` заголовком и примером. Самих патчей сейчас нет (нечего патчить) — это норма и контракт на будущее.

### D5. Параметризация таймаутов ожидания
`reply_timeout_seconds` уже параметр `run()`. Добавляем `clarify_timeout_seconds` (по умолч. `14*24*3600`) и `reactivation_timeout_seconds` (по умолч. `30*24*3600`) как параметры `run()`; `TemporalWorkflowGateway` тянет их из `Settings`. Магические числа из тела воркфлоу убираются.

### D6. Новые настройки
В `Settings`: `workflow_continue_as_new_threshold: int = 5`, `llm_activity_timeout_seconds: int = 180`, `clarify_timeout_seconds`, `reactivation_timeout_seconds`. `Config` остаётся source-of-truth.

### D7. Идемпотентность старта
`start_booking` всегда генерит новый `uuid4` — два форварда = два воркфлоу. В рамках этого change не решаем (это поведение IntakeService, не выполнения воркфлоу). Фиксируем как Open Question.

### D8. Continue-As-New handoff через конкретный `RunInput` (находка при реализации)
Изначально планировался union `start: ForwardInput | ResumeInput`. На практике дефолтный Temporal data-converter **не десериализует** union верхнего уровня: `TypeAdapter("ForwardInput | ResumeInput")` (строковая аннотация из `from __future__ import annotations`) не строится → `start` приходит в воркфлоу как `dict` → `AttributeError`. Решение — конкретный wrapper `RunInput { forward: ForwardInput | None, resume: ResumeInput | None }`: converter видит один конкретный тип, а union живёт *внутри* pydantic-модели, где разрешается нативно. Смены глобального data-converter не требуется.

### D9. Десериализация run-args требует полного набора аргументов (гатча, находка)
 temporalio применяет type-hint к input-args только когда число переданных args **совпадает** с числом параметров `run`. При частичной передаче (defaults) args десериализуются без hint → pydantic-DTO приходят как `dict`. Поэтому `start_workflow` (gateway и тесты) обязан передавать **все** параметры `run` позиционно. Зафиксировано в тестах и gateway.

### D10. E2E против docker-compose
E2E-тесты умеют работать против внешнего сервера через `KKR_E2E_TEMPORAL_TARGET=localhost:7233` (docker compose). Для внешнего сервера введён shim `_ServerEnv` с методом `new_worker`, т.к. `WorkflowEnvironment.from_client` намеренно не предоставляет `new_worker` (реальный сервер не хостит воркеров). Без переменной тесты падают на `WorkflowEnvironment.start_local()` (качает dev-сервер).

## Risks / Trade-offs

- **Continue-As-New теряет in-flight сигналы, если их забыть передать** → «mailbox» необслуженных сигналов передаётся стартовым аргументом; покрывается E2E-сценарием «ответ пришёл во время сброса истории».
- **Bounded retry = воркфлоу падает при длительной недоступности БД/LLM** → сознательный trade-off. Активности идемпотентны, а упавший воркфлоу виден в Visibility и может быть перезапущен. Документируем. Альтернатива (infinite retry) хуже — молчаливое зависание и рост счетов.
- **`workflow.patched` «на будущее» без текущих патчей выглядит мёртвым кодом** → это контракт, не код; фиксируем только правило в комментарии/документации, без пустых вызовов.
- **Поднятие `start_to_close_timeout` для LLM до 180s задерживает detection зависания** → компенсируем bounded retry (D2): даже 3 попытки по 180s ограничены.
- **E2E зависит от скачиваемого dev-сервера** → остаётся за `KKR_E2E_TEMPORAL=1`; оффлайн-сьют не зависит.

## Migration Plan

1. Фикс регистрации (D1) — деплой сразу, без миграции данных.
2. Retry/timeout (D2, D5, D6) — деплой; запущенных воркфлоу ещё нет (v1), конфликтов нет.
3. Continue-As-New (D3) — счётчик instance-local (не в `BookingState`), новый DTO `ResumeInput`; `BookingState` не меняется, старые payload'ы совместимы.
4. Версионирование (D4) — контракт-документация; rollback не нужен.
5. **Rollback**: каждое изменение независимо и обратно-совместимо (новые поля с дефолтами, новые параметры с дефолтами). Откат — revert кода; воркфлоу пересоздаются.

## Open Questions

- **Q1 (идемпотентность старта)**: детерминировать `booking_id` из хэша forward-а + `IdReusePolicy`, либо дедупить в `IntakeService`? Вынести в отдельный change (затрагивает intake, не execution).
- **Q2 (continue-as-new threshold)**: 5 туров — оценка; реальное число стоит калибровать по реальному размеру истории (метрики). Оставить настраиваемым.
- **Q3 (non-retryable LLM-ошибки)**: какие ошибки модели считать невосстановимыми (напр. 4xx auth)? Зависит от провайдера; начать с пустого списка, уточнять по факту.
