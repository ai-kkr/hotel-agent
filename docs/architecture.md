# Архитектура

Обзор компонентов системы и того, как данные проходят от сообщения гостя в Telegram до
переписки с отелем и обратно. Документ описывает фактическое состояние кода в [`src/`](../src/).

> Документацию по поведению самого агента (роль, инструменты, промпты) см. в
> [agent.md](agent.md); настройку окружения и запуск — в [development.md](development.md).

## Общая схема

```
 Telegram ──► aiogram (src/bot) ──► agent_step (src/temporal/client)
 Mailtrap inbound webhook (src/app) ─┘            │
                                                  ▼
                          signal-with-start ──► Temporal AgentQueue (per thread_id)
                                                  │  (сериализует ходы одного клиента)
                                                  ▼
                                   execute_child_workflow ──► AgentWorkflow (src/temporal/agent_runner)
                                                  │   load_state (activity) → InMemorySaver → g.ainvoke
                                                  ▼
                                   LangGraph-агент (src/agent): узлы бегут как Temporal-активности
                                                  │   summarize_check ─► model ──► tools ──► model … ──► cleanup ──► END
                                                  │      (→ summarize → model, когда input_tokens > порога)
                                                  ▼
                                     tools: set_booking_info, send_wishes_to_hotel, reply_to_hotel,
                                     search_internet, extract_web_page, inform_step, cancel_task,
                                     set/list/update/cancel_scheduled_task
                            ┌─────────────────────────────────────┼──────────────────────────┐
                            ▼                                     ▼                          ▼
                      PostgreSQL (src/db)              Mailtrap send (письмо отелю)    Tavily (поиск)
                       states (state) /                       │
                       outbound_emails                        ▼
                            ▲                        отель отвечает ──► Mailtrap inbound
                            │                                              │
                  save_state (activity)                        ▼
                          webhook Mailtrap (src/app/webhook) ◄── HTTP POST с подписью
                                  │
                                  └── In-Reply-To совпал с outbound? ──► ход "hotel reply:" (+ state_update)
                                  └── иначе ──► это пересланное письмо гостя ──► ход "forwarded email:"

   Temporal Schedules ──(по расписанию)──► ScheduledTurn ──activity──► enqueue_scheduled_turn
                                              └── signal-with-start ──► AgentQueue (как обычный ход)
```

## Компоненты

### `main.py` — точка входа

`build_context()` ([`src/context.py`](../src/context.py)) создаёт разово всё, что не требует
запущенного event-loop: `Bot` (aiogram), `MailtrapClient`, async-движок и `session_factory`,
`TavilyClient`. Чат-модель строится лениво (`build_model`) внутри ноды `model` — в `ApplicationContext`
её нет. Затем `create_app(ctx)` собирает FastAPI-приложение, а `uvicorn.run` поднимает сервер. В
`lifespan`: запускается задача polling'а бота и **Temporal-воркер** (`run_worker`,
[`src/temporal/worker.py`](../src/temporal/worker.py)) — он подключается к
`KKR_TEMPORAL_TARGET`, регистрирует воркфлоу `AgentQueue` + `AgentWorkflow` + `ScheduledTurn`,
активности `load_state`/`save_state`/`enqueue_scheduled_turn` и плагин `LangGraphPlugin` (граф
`"agent"` = `build_email_agent()`); воркер
бежит на `UnsandboxedWorkflowRunner`, т. к. песочница Temporal не дружит с импортами langgraph/langchain.
При остановке аккуратно гасятся: polling, http-сессия aiogram (иначе uvicorn виснет при завершении)
и воркер (`worker.shutdown()`), и сбрасываются очереди Langfuse.

### Контекст приложения — `src/context.py`

Процесс-синглтон `ApplicationContext` (`get_context()` / `set_context()`), доступный из любого
места. Несёт только тяжёлые **несериализуемые** зависимости: `Bot` (aiogram), `MailtrapClient`,
`TavilyClient` и `session_factory`; плюс лениво подключаемый `temporal_client`
(`get_temporal_client()` — одно `Client.connect(..., data_converter=message_aware_data_converter)`
на процесс, переиспользуется тулами планирования и активностью `enqueue_scheduled_turn`). Чат-модели
здесь нет — её строит нода `model`. Инструменты и активности достают нужное **лениво**, прямо внутри
себя (см. [«Сериализуемый контекст»](#сериализуемый-контекст-агента)).

### Telegram-бот — `src/bot`

- [`core.py`](../src/bot/core.py) — `Dispatcher` с обработчиками:
  - `/start` ([`command_start_handler`](../src/bot/core.py)) — регистрирует клиента (если ещё
    нет) и шлёт приветствие с личным адресом для пересылки брони;
  - `/new` ([`command_new_handler`](../src/bot/core.py)) — сбрасывает контекст агента для клиента:
    удаляет строку состояния в `states` (`delete_state_by_client_id`, ключ — `clients.id`; история
    сообщений, данные брони, wishes, threading-состояние — всё) **и отменяет все запланированные
    задачи клиента** (`cancel_all_scheduled_tasks` — Temporal-расписание + строку каталога
    `scheduled_tasks`), чтобы никакая задача не стрельнула в уже пустой контекст. Записи
    `outbound_emails` остаются в Postgres, поэтому запоздавший ответ отеля всё равно
    смаршрутизируется — в уже пустой контекст;
  - любое текстовое сообщение ([`chat_handler`](../src/bot/core.py)) — ставит ход агента в очередь
    через `agent_step` (Temporal) и сразу возвращает управление; ответ агент пришлёт сам из своих
    активностей. Сообщения, начинающиеся с `/`, игнорируются (неизвестная команда). Перед отправкой
    в агента к тексту пришпиливается текущее время клиента (`build_now_context`: UTC + зоны
    дома/поездки, если заданы) — штамп лежит **в human-message** (хвост запроса), чтобы не ломать
    prefix-cache; зоны читаются из state JSONB через `ClientRepository.get_timezones`;
  - `@dp.errors()` — прокидывает исключения обработчиков в лог, чтобы aiogram не глотал их
    молча.
- [`app.py`](../src/bot/app.py) — `run_bot()`: регистрирует список команд (`/start`, `/new`) и
  запускает `dp.start_polling`.
- [`templates.py`](../src/bot/templates.py) + `templates/greeting.md.j2` — Jinja-шаблон
  приветствия (адрес inbound-ящика подставляется в `<code>`).

### Агент — `src/agent`

Один ReAct-агент на рукописном [`langgraph.graph.StateGraph`](../src/agent/agent.py) (узлы `model` +
`tools` + `cleanup` + `summarize`) — без `create_agent`. Граф исполняется Temporal LangGraph-плагином, каждый узел
бегёт как активность. Подробно — в [agent.md](agent.md). Здесь — только структурные файлы:

- [`state.py`](../src/agent/state.py) — `EmailState` (наследник `AgentState`) с полями брони,
  пожеланиями, флагом отмены, полями threading'а и полями саммаризации (`conversation_summary`,
  `last_prompt_tokens`). Поля брони используют reducer `booking_field` (см. ниже). Новые поля
  саммаризации — чистый JSON, без своего редьюсера.
- [`context.py`](../src/agent/context.py) — `EmailContext` (TypedDict): только плоские данные
  (`from_email`, `reply_to`, `user_email`, `client_id`, `telegram_id`). Никаких объектов.
- [`agent.py`](../src/agent/agent.py) — `build_email_agent()`: строит граф
  `summarize_check → model → tools → model … → cleanup → END` (вход в `model` gated `summarize_check`:
  при `last_prompt_tokens` > порога сначала `summarize → model`), навешивая на каждый узел декораторы-хелперы
  (langfuse, typing) и оборачивая вызовы тул через `run_tool_call` (retry + self-correction). `tool_path`
  маршрутизирует `model` → `"tools"` (есть tool-calls) / `"cleanup"` (ход завершается и есть что
  архивировать) / `"__end__"` (шорткат — архивировать нечего, `cleanup` не выполняется).
- [`compaction.py`](../src/agent/compaction.py) — компактизация контекста: нода `cleanup` в конце
  хода замещает тяжёлый контент `ToolMessage` от `search_internet` / `extract_web_page` коротким
  стабом **на месте** через id-upsert штатного редьюсера `add_messages` (свой редьюсер не вводится),
  сохраняя `id` / `tool_call_id` / `name` и помечая `additional_kwargs["archived"]=True`. Вайтлист —
  по имени тулы, не по размеру. Чистый Python, без LLM/`get_context()`/миграций.
- [`summarization.py`](../src/agent/summarization.py) — авто-саммаризация длинной переписки: нода
  `summarize` сжимает старый префикс истории в бегущее поле `conversation_summary` и удаляет его через
  `RemoveMessage` (штатный `add_messages` выкидывает по id), оставляя recency-окно. Триггер
  реактивный — по `usage_metadata["input_tokens"]` прошлого вызова модели; граница среза не разрывает
  пару `AIMessage(tool_calls) ↔ ToolMessage`. Саммаризационный вызов cache-aware: `SYSTEM_MAIN` остаётся
  системным промптом, инструкция идёт хвостовой `HumanMessage`. Новые поля стейта — чистый JSON, **без
  миграции и без изменений data converter**.
- [`middleware.py`](../src/agent/middleware.py) — `run_tool_call`: повторяет транзиентные сбои тул по
  per-tool-политике и превращает `SelfCorrectionError` в `ToolMessage`-подсказку (поведение бывших
  middleware — см. [agent.md](agent.md#самокоррекция)).
- [`utils.py`](../src/agent/utils.py) — `send_telegram_reply`: отправка ответа модели в чат гостя с
  подстановкой `$user_inbox` (живёт в слое агента, чтобы тулы могли импортировать напрямую).
- [`helpers/`](../src/agent/helpers) — чистые хелперы нод, развязанные с `EmailContext`/`Runtime`
  (принимают примитивы): [`langfuse.py`](../src/agent/helpers/langfuse.py)
  (`with_langfuse`/`inject_langfuse_callback`), [`telegram.py`](../src/agent/helpers/telegram.py)
  (индикатор «печатает…»), [`openrouter.py`](../src/agent/helpers/openrouter.py) (sticky-session
  для OpenRouter).

### Temporal — `src/temporal`

Оркестрация хода агента (агентной логики здесь нет — граф живёт в `src/agent`):

- [`client.py`](../src/temporal/client.py) — `agent_step`: кладёт ход агента в очередь клиента через
  signal-with-start (`start_workflow(AgentQueue, start_signal=add_task, …)`); опциональный
  `state_update` — частичный merge state перед ходом.
- [`queue.py`](../src/temporal/queue.py) — `AgentQueue` (один воркфлоу на `thread_id`): сериализует
  ходы одного клиента, ходы разных клиентов бегут параллельно; завершается, когда очередь пуста.
- [`agent_runner.py`](../src/temporal/agent_runner.py) — `AgentWorkflow`: один ход = `load_state`
  → (опц. `state_update`) → `g.ainvoke` (`InMemorySaver` в рамках хода) → `save_state`. Langfuse
  trace id детерминированно выводится из `run_id` (см. [architecture.md gotchas](#../CLAUDE.md)).
- [`activities.py`](../src/temporal/activities.py) — `load_state`/`save_state`: (де)сериализация
  `EmailState` через `ClientRepository`; плюс `enqueue_scheduled_turn(run_input)` — активность
  воркфлоу `ScheduledTurn`, делающая signal-with-start на `queue:{thread_id}` (тот же путь, что и
  `agent_step`), через `get_context().temporal_client`.
- [`scheduled_turn.py`](../src/temporal/scheduled_turn.py) — `ScheduledTurn`: тривиальный воркфлоу,
  который Temporal Schedule стартует на каждое срабатывание (Schedule не умеет signal-with-start,
  только старт воркфлоу); его единственная активность — `enqueue_scheduled_turn`.
- [`schedules.py`](../src/temporal/schedules.py) — тонкая обёртка над Temporal Schedule API для
  запланированных задач: `create_or_idempotent` / `list_for_client` / `update` / `delete`; id
  `kkr-sched:{client_id}:{task_key}`, перевод модели `ScheduleInput` в `ScheduleSpec` (наивное
  локальное время + выбранная зона как `time_zone_name`), сборка `RunInput` хода.
- [`converter.py`](../src/temporal/converter.py) — `message_aware_data_converter`: восстанавливает
  классы langchain-сообщений и `Command` после декода, чтобы они пережили границу workflow↔activity.
- [`worker.py`](../src/temporal/worker.py) — `run_worker`: подключение к Temporal, регистрация
  воркфлоу (`AgentQueue`, `AgentWorkflow`, `ScheduledTurn`) и активностей (`load_state`,
  `save_state`, `enqueue_scheduled_turn`) и плагина.

### FastAPI и webhook — `src/app`

- [`factory.py`](../src/app/factory.py) — `create_app()`: FastAPI + lifespan (запуск бота и
  Temporal-воркера), подключается только роутер вебхука.
- [`webhook.py`](../src/app/webhook.py) — единственный эндпоинт `POST /send_test_email`,
  принимающий inbound-webhook Mailtrap. Подпись проверяется зависимостью. Логика маршрутизации —
  см. [«Входящие письма»](#входящие-письма-webhook).
- [`dependencies.py`](../src/app/dependencies.py) — `AppSettings`, `AppSession` (DB-сессия на
  запрос) и `verify_mailtrap_signature` (HMAC по raw-телу запроса).

### База данных — `src/db`

SQLAlchemy 2 (async, asyncpg). Модели в [`models.py`](../src/db/models.py):

- **`ClientORM`** (`clients`) — связь Telegram-пользователя с его inbound-ящиком Mailtrap.
  Свойство `thread_id = "client:{id:04d}"` — ключ thread'а агента (история переписки привязана к
  клиенту).
- **`ForwardedEmailORM`** (`forwarded_emails`) — пересланные гостем письма (сам текст брони);
  тело хранится как типизированный `MessageDetails` (`MessageDetailsType`).
- **`OutboundEmailORM`** (`outbound_emails`) — отправленные агентом письма (`message_id`,
  `subject`, `in_reply_to`). Нужна для сопоставления ответа отеля по `In-Reply-To`.
- **`StateORM`** (`states`) — сохранённое состояние агента для клиента. Одна строка на клиента
  (`client_id` — первичный ключ-FK), колонка `state` хранит сериализованный `EmailState` как
  `JSONB` (на Postgres) / `JSON` (SQLite в тестах); `StateType`
  ([`types.py`](../src/db/types.py)) прозрачно (де)сериализует единственное не-JSON-поле —
  `messages` (langchain `BaseMessage`) через `messages_to_dict`/`messages_from_dict`.
- **`ScheduledTaskORM`** (`scheduled_tasks`) — **каталог** запланированных задач клиента (индекс для
  `list`/existence). PK `(client_id, task_key)` (+ ведущий префиксный индекс по `client_id`); несёт
  display-метаданные (`description`, `spec_summary`, `paused`, `remaining`). Само *срабатывание*
  живёт в Temporal Schedule (id `kkr-sched:{client_id}:{task_key}`); эта таблица — только каталог,
  потому что `list_schedules` не умеет фильтровать расписания серверно. Синхронизируется на каждом
  create/update/cancel (Temporal-запись и каталог; см. риски в
  [design.md](../openspec/changes/add-scheduled-tasks/design.md)).

[`repositories.py`](../src/db/repositories.py) — `ClientRepository`: поиск клиента по
`telegram_id` / `email` / `inbox` / `inbox_id`, создание клиента (с автоматическим
provisioning'ом inbound-ящика), запись пересланных и отправленных писем, а также
чтение/запись/удаление состояния агента (`get_state_by_client_id` / `set_state_by_client_id` /
`delete_state_by_client_id`), а также дешёвое чтение часовых поясов клиента из JSONB
(`get_timezones` — для штампа текущего времени в чате). Рядом — `ScheduledTaskRepository`: CRUD
над каталогом запланированных задач (`list_by_client` / `keys_for_client` / `get` / `upsert` /
`delete`). [`session.py`](../src/db/session.py)
— движок с `pool_pre_ping`/`pool_recycle` против «протухших» asyncpg-соединений и
`session_context` (async-contextmanager с автокоммитом).

### Интеграция с Mailtrap — `src/integrations/mailtrap`

[`client.py`](../src/integrations/mailtrap/client.py) — `MailtrapClient`:

- `send(...)` — транзакционное письмо через `send.api.mailtrap.io`; вариант тела
  (`TextAndHTML`/`TextOnly`/`HTMLOnly`) выбирается по наполнению, кастомные `headers` — для
  `In-Reply-To`/`References`;
- `get_message(message_id, inbox_id)` — забрать inbound-письмо целиком;
- `provision_inbox(name)` — создать клиенту личный inbound-ящик (вызывается при регистрации
  клиента).

Рядом — vendored OpenAPI-клиенты `mailtrap_inbound/`, `mailtrap_send/`, `mailtrap_sending/`
(сгенерированы [`scripts/generate_mailtrap_client.py`](../scripts/generate_mailtrap_client.py);
руками не правятся и исключены из ruff). [`webhooks.py`](../src/integrations/mailtrap/webhooks.py) —
pydantic-модель `InboundWebhookPayload`.

## Жизненный цикл задачи

1. **Регистрация.** Гость шлёт `/start` → `ClientRepository.add_client` провижнит личный
   inbound-ящик и сохраняет клиента. Адрес ящика показывается гостю.
2. **Сообщение гостя.** Текст из чата → `chat_handler` → `agent_step(msg, client)`. Ход встаёт в
   очередь клиента (Temporal) и ставит граф: `load_state` → `g.ainvoke` → `save_state`. Агент
   определяет, есть ли данные брони; если нет — просит переслать подтверждение на `$user_inbox`.
3. **Пересланное письмо.** Гость пересылает бронь на свой inbound-адрес → Mailtrap шлёт webhook →
   `webhook.py` забирает тело и вызывает `agent_step` с сообщением вида
   `forwarded email:\n<text>` (так агент «видит» содержимое брони).
4. **Отправка письма отелю.** Агент собирает бронь через `set_booking_info` и вызывает
   `send_wishes_to_hotel` — тул генерирует письмо на `hotel_language`, отправляет через Mailtrap и
   сохраняет `OutboundEmailORM` (с `message_id`).
5. **Ответ отеля.** Отель отвечает → webhook → по `In-Reply-To` находится соответствующий
   `outbound_emails` → `_handle_hotel_reply` вызывает `agent_step` с ходом `hotel reply:\n<body>` и
   `state_update={"last_hotel_message_id", "last_hotel_subject"}` — заголовки threading'а мерджатся
   в state внутри воркфлоу перед ходом (атомарно). Агент действует проактивно (см. [agent.md](agent.md))
   и при необходимости отвечает через `reply_to_hotel`.

## Ключевая механика

### Сериализуемый контекст агента

`EmailContext` ([`src/agent/context.py`](../src/agent/context.py)) несёт **только плоские
данные** — это сознательное ограничение: контекст пересекает границу workflow↔activity через
data-converter Temporal и должен быть полностью сериализуемым. Все «тяжёлые» объекты (chat-модель,
Mailtrap, Tavily, DB-фабрика) тулы и активности достают лениво через `get_context()` **внутри себя**,
а не через параметры. Побочный эффект — разрыв потенциального цикла импортов `context ↔ agent`.

### Threading переписки с отелем

- Исходящее письмо (`send_wishes_to_hotel`) отправляется с `Reply-To: <inbox гостя>`, чтобы
  ответ отеля вернулся в его inbound-ящик. `message_id` отправленного письма сохраняется в
  `outbound_emails` и кладётся в state (`last_outbound_message_id`).
- Входящий webhook по `msg.in_reply_to` находит запись `outbound_emails` → это **ответ отеля**.
  В state проставляются `last_hotel_message_id` и `last_hotel_subject`.
- Ответ агенту (`reply_to_hotel`) шлётся с заголовками `In-Reply-To`/`References` = последний
  `message_id` отеля и темой `Re: <subject>` — так письма держатся в одной ветке.

### Подстановка `$user_inbox`

Агент не знает реального адреса ящика гостя и пишет в ответах плейсхолдер `$user_inbox`
дословно. Подстановка реального `ClientORM.inbox` (он же `EmailContext.reply_to`) делается при
рендере сообщения в чат в `send_formatted` ([`src/bot/utils.py`](../src/bot/utils.py)) — адрес
**оборачивается в `<pre>` блок** (моноширинно, копируется одним тапом), а висящая пунктуация
сразу после плейсхолдера (`. , ; : ! ?`) поглощается, чтобы не болталась хвостом.
Нода `model` отправляет свой ответ через `send_telegram_reply`
([`src/agent/utils.py`](../src/agent/utils.py)); вебхук использует ту же `send_formatted` **без**
подстановки (`inbox=""`) для уведомлений о входящих письмах.

### HTML → Telegram

Агент emits Telegram-HTML напрямую (`<b>`, `<i>`, `<code>`, `<a>`); `send_formatted`
([`src/bot/utils.py`](../src/bot/utils.py)) отправляет его с `parse_mode=HTML`. Длинные сообщения
режутся по лимиту 4096 UTF-16 код-юнитов по границам строк; при ошибке отправки остаётся
fallback на plain text (теги срезаются). Неподконтрольный текст (sender/subject из вебхука)
HTML-экранируется через `aiogram.utils.text_decorations.html_decoration.quote`.

### Reducer `booking_field`

Поля брони в `EmailState` (`hotel_name`, `booking_ref`, `from_date`, `to_date`, `hotel_email`,
`guests`, `hotel_language`, `home_timezone`, `trip_timezone`) используют редьюсер «keep existing when
update is `None`». Это позволяет агенту вызывать `set_booking_info` с любым подмножеством полей за
один `Command(update=...)`, а пропущенные (`None`) оставить нетронутыми — вместо того чтобы затирать
их. Обязательных полей шесть (всё кроме `booking_ref`); `missing_booking_fields` проверяет именно их.
Поля `home_timezone`/`trip_timezone` (IANA-имена) анкорят время запланированных задач — не обязательны
для отправки письма, но нужны для тула `set_scheduled_task`.
