## 1. Исправление регистрации активностей

- [x] 1.1 В `src/infrastructure/workflows/worker.py` заменить `activities=[activities]` на явный список bound-методов (`extract`, `discover_contact`, `agent_turn`, `send_email`, `build_report`, `relay_to_client`, `update_booking_state`, `record_inbound_reply`); удалить устаревший комментарий про «class instance at runtime»
- [x] 1.2 В `tests/workflows/test_workflow_integration.py` привести регистрацию в `env.new_worker(...)` к тому же списку bound-методов
- [x] 1.3 Проверено против docker-compose Temporal: `Worker(...)` конструируется и опрашивает task queue без `TypeError` (скрипт-верификация через `build_client`/`build_worker`)

## 2. Retry-политики и таймауты

- [x] 2.1 В `src/infrastructure/workflows/workflow.py` ввести константы политик: `LLM_RETRY_POLICY` (max_attempts=3), `SIDE_EFFECT_RETRY_POLICY` (max_attempts=5), `DISCOVERY_RETRY_POLICY` (max_attempts=3) через `temporalio.common.RetryPolicy`
- [x] 2.2 Ввести константы таймаутов: `LLM_ACTIVITY_TIMEOUT = 180s`, оставить `ACTIVITY_TIMEOUT = 120s` для прочих
- [x] 2.3 В `workflow.py` проставить `retry_policy=` и соответствующий `start_to_close_timeout=` во всех вызовах `workflow.execute_activity` (`extract`, `agent_turn` — LLM; `discover_contact` — discovery; `send_email`, `relay_to_client`, `build_report`, `update_booking_state`, `record_inbound_reply` — side-effect)
- [x] 2.4 В `src/infrastructure/config.py` добавить настройку `llm_activity_timeout_seconds: int = 180` (дефолт таймаута зафиксирован в константе `LLM_ACTIVITY_TIMEOUT`; настройка документирует операционное значение)

## 3. Continue-As-New

- [x] 3.1 Ввести **instance-local** счётчик `self._negotiation_runs` в `BookingWorkflow.__init__` (не в `BookingState` — он должен сбрасываться на новом run, иначе порог сработает сразу → бесконечный цикл)
- [x] 3.2 Инкрементировать `self._negotiation_runs` в `_negotiate` перед каждым agent-turn
- [x] 3.3 Реализовать сброс: при `self._negotiation_runs >= threshold` вызывать `workflow.continue_as_new`, передавая `ResumeInput(state, trigger, in-flight-сигналы)` как стартовый аргумент
- [x] 3.4 В `src/infrastructure/config.py` добавить `workflow_continue_as_new_threshold: int = 5`; пробросить в `run()` как параметр и из `TemporalWorkflowGateway`

## 4. Параметризация таймаутов ожидания

- [x] 4.1 Добавить параметры `run()`: `clarify_timeout_seconds` (default `14*24*3600`), `reactivation_timeout_seconds` (default `30*24*3600`); убрать литералы 14/30 дней из `_await_followup` и `_await_reactivation`
- [x] 4.2 В `config.py` добавить `clarify_timeout_seconds` и `reactivation_timeout_seconds`; в `TemporalWorkflowGateway` (и его вызове в `runtime/local.py`) передавать их в `start_workflow(... args=[...])`

## 5. Контракт версионирования

- [x] 5.1 В шапке `workflow.py` задокументировать контракт: любое изменение структуры команд оборачивается в `workflow.patched("<change-id>")` с примером блока; самих патчей сейчас не вводить (nечего патчить)

## 6. Тесты

- [x] 6.1 В `tests/workflows/test_workflow_integration.py` регистрация приведена к bound-методам; args совместимы с новой сигнатурой `run()` _(прогон под `KKR_E2E_TEMPORAL=1` — см. 7.3)_
- [x] 6.2 Добавлен E2E-сценарий `test_llm_activity_retry_is_bounded` (в `tests/workflows/test_workflow_hardening.py`): стабовый LLM-агент падает, активность делает ровно 3 попытки, воркфлоу завершается ошибкой
- [x] 6.3 Добавлен E2E-сценарий `test_continue_as_new_transfers_state_and_resumes`: при threshold=2 и 3 турах воркфлоу делает continue-as-new, переносит состояние (topic-id) и доходит до отчёта
- [x] 6.4 Оффлайн-сьют (`pytest` без `KKR_E2E_TEMPORAL`) зелёный (177 passed, 3 skipped); новые E2E-сценарии помечены `skipif`

## 7. Валидация

- [x] 7.1 `openspec validate harden-temporal-workflows` проходит без ошибок
- [x] 7.2 `pytest` (оффлайн) зелёный — 177 passed, 3 skipped, покрытие 90.42%
- [x] 7.3 `KKR_E2E_TEMPORAL=1 KKR_E2E_TEMPORAL_TARGET=localhost:7233 pytest tests/workflows` зелёный против docker-compose Temporal — 35 passed (3 gated E2E включены: bounded retry, continue-as-new, integration)

## 8. Находки при реализации (доп. фикс)

- [x] 8.1 Ввести `RunInput` (конкретный wrapper с опциональными `forward`/`resume`) вместо union `ForwardInput | ResumeInput` в сигнатуре `run` — дефолтный data-converter не десериализует union верхнего уровня (TypeAdapter не строится из строковой аннотации), `start` приходил как `dict`
- [x] 8.2 В тестах/E2E запускать воркфлоу с **полным** набором args сигнатуры `run` — при передаче fewer args temporalio десериализует без type-hint → `dict` (гатча)
- [x] 8.3 E2E-тесты умеют работать против внешнего сервера через `KKR_E2E_TEMPORAL_TARGET` (docker compose), иначе падают на скачиваемый dev-сервер (`WorkflowEnvironment.start_local`); для внешнего сервера введён shim `_ServerEnv` с `new_worker`, т.к. `WorkflowEnvironment.from_client` не предоставляет `new_worker`
