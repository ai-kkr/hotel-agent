# Архитектура

Обзор компонентов системы и того, как данные проходят от сообщения гостя в Telegram до
переписки с отелем и обратно. Документ описывает фактическое состояние кода в [`src/`](../src/).

> Документацию по поведению самого агента (роль, инструменты, промпты) см. в
> [agent.md](agent.md); настройку окружения и запуск — в [development.md](development.md).

## Общая схема

```
 Telegram ──► aiogram (src/bot) ──► stream_graph ──► LangGraph-агент (src/agent)
                                                                  │
                                                                  ▼
                                                     tools: set_booking_info,
                                                     send_wishes_to_hotel, reply_to_hotel,
                                                     search_internet, extract_web_page,
                                                     inform_step, cancel_task
                                                                  │
                            ┌─────────────────────────────────────┼──────────────────────────┐
                            ▼                                     ▼                          ▼
                      PostgreSQL (src/db)              Mailtrap send (письмо отелю)    Tavily (поиск)
                            ▲                                     │
                            │                                     ▼
                  outbound_emails (запись)              отель отвечает ──► Mailtrap inbound
                                                                        │
                                                                        ▼
                          webhook Mailtrap (src/app/webhook) ◄── HTTP POST с подписью
                                  │
                                  └── In-Reply-To совпал с outbound? ──► ход "hotel reply:" в агента
                                  └── иначе ──► это пересланное письмо гостя ──► ход "forwarded email:"
```

## Компоненты

### `main.py` — точка входа

`build_context()` ([`src/context.py`](../src/context.py)) создаёт все тяжёлые зависимости разово:
`Bot` (aiogram), `MailtrapClient`, async-движок и `session_factory`, chat-модель (`build_model`),
`TavilyClient` и пул чекпоинтера LangGraph (`AsyncConnectionPool` для `AsyncPostgresSaver`,
`open=False`). Сам граф агента и saver строятся **позже** — в `lifespan` приложения через
`init_graph()` (см. ниже почему). Затем `create_app(ctx)` собирает FastAPI-приложение, а
`uvicorn.run` поднимает сервер. В `lifespan`: открывается пул и применяется схема чекпоинтера
(`setup()`), запускается задача polling'а бота, а при остановке — пул и http-сессия aiogram
аккуратно гасятся (иначе uvicorn виснет при завершении) и сбрасываются очереди Langfuse.

### Контекст приложения — `src/context.py`

Процесс-синглтон `ApplicationContext` (`get_context()` / `set_context()`), доступный из любого
места. Нужен, прежде всего, инструментам агента: они достают оттуда chat-модель, Mailtrap-клиент,
Tavily и `session_factory` **лениво**, прямо внутри тулы. Это не случайность — см.
[«Сериализуемый контекст»](#сериализуемый-контекст-агента).

### Telegram-бот — `src/bot`

- [`core.py`](../src/bot/core.py) — `Dispatcher` с обработчиками:
  - `/start` ([`command_start_handler`](../src/bot/core.py)) — регистрирует клиента (если ещё
    нет) и шлёт приветствие с личным адресом для пересылки брони;
  - `/new` ([`command_new_handler`](../src/bot/core.py)) — сбрасывает контекст агента для клиента:
    удаляет все чекпойнты треда через `AsyncPostgresSaver.adelete_thread` (история сообщений,
    данные брони, wishes, threading-состояние — всё). Записи `outbound_emails` остаются в Postgres,
    поэтому запоздавший ответ отеля всё равно смаршрутизируется — в уже пустой тред;
  - любое текстовое сообщение ([`chat_handler`](../src/bot/core.py)) — маршрутируется в агента
    через `stream_graph`. Сообщения, начинающиеся с `/`, игнорируются (неизвестная команда);
  - `@dp.errors()` — прокидывает исключения обработчиков в лог, чтобы aiogram не глотал их
    молча.
- [`app.py`](../src/bot/app.py) — `run_bot()`: регистрирует список команд (`/start`, `/new`) и
  запускает `dp.start_polling`.
- [`templates.py`](../src/bot/templates.py) + `templates/greeting.md.j2` — Jinja-шаблон
  приветствия (адрес inbound-ящика подставляется в `<code>`).

### Агент — `src/agent`

Один ReAct-агент через [`langchain.agents.create_agent`](../src/agent/agent.py), без рукописных
графов. Подробно — в [agent.md](agent.md). Здесь — только структурные файлы:

- [`state.py`](../src/agent/state.py) — `EmailState` (наследник `AgentState`) с полями брони,
  пожеланиями, флагом отмены и полями threading'а. Поля брони используют reducer `booking_field`
  (см. ниже).
- [`context.py`](../src/agent/context.py) — `EmailContext` (TypedDict): только плоские данные
  (`from_email`, `reply_to`, `user_email`, `client_id`). Никаких объектов.
- [`stream.py`](../src/agent/stream.py) — `stream_graph()`: гоняет один ход агента (или
  возобновляет `interrupt`), стримит narration и финальные сообщения в чат, держит «печатает…».
- [`middleware.py`](../src/agent/middleware.py) — `SelfCorrectionMiddleware` перехватывает
  `SelfCorrectionError` из тул и превращает его в `ToolMessage`-подсказку для следующего хода.

### FastAPI и webhook — `src/app`

- [`factory.py`](../src/app/factory.py) — `create_app()`: FastAPI + lifespan (запуск бота),
  подключается только роутер вебхука.
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

[`repositories.py`](../src/db/repositories.py) — `ClientRepository`: поиск клиента по
`telegram_id` / `email` / `inbox` / `inbox_id`, создание клиента (с автоматическим
provisioning'ом inbound-ящика), запись пересланных и отправленных писем. [`session.py`](../src/db/session.py)
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
2. **Сообщение гостя.** Текст из чата → `chat_handler` → `stream_graph(msg, client)`. Агент
   определяет, есть ли данные брони; если нет — просит переслать подтверждение на `$user_inbox`.
3. **Пересланное письмо.** Гость пересылает бронь на свой inbound-адрес → Mailtrap шлёт webhook →
   `webhook.py` забирает тело и запускает `stream_graph` с сообщением вида
   `forwarded email:\n<text>` (так агент «видит» содержимое брони).
4. **Отправка письма отелю.** Агент собирает бронь через `set_booking_info` и вызывает
   `send_wishes_to_hotel` — тул генерирует письмо на `hotel_language`, отправляет через Mailtrap и
   сохраняет `OutboundEmailORM` (с `message_id`).
5. **Ответ отеля.** Отель отвечает → webhook → по `In-Reply-To` находится соответствующий
   `outbound_emails` → агенту подаётся ход `hotel reply:\n<body>` (а в state кладутся
   `last_hotel_message_id` / `last_hotel_subject` для threading'а ответа). Агент действует
   проактивно (см. [agent.md](agent.md)) и при необходимости отвечает через `reply_to_hotel`.

## Ключевая механика

### Сериализуемый контекст агента

`EmailContext` ([`src/agent/context.py`](../src/agent/context.py)) несёт **только плоские
данные** — это сознательное ограничение: рантайм-контекст LangGraph должен быть полностью
сериализуемым (чекпоинты состояния). Все «тяжёлые» объекты (chat-модель, Mailtrap, Tavily,
DB-фабрика) тулы достают лениво через `get_context()` **внутри себя**, а не через параметры.
Побочный эффект — разрыв потенциального цикла импортов `context ↔ agent`.

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
дословно. Подстановка реального `ClientORM.inbox` делается при рендере сообщения в чат — уже
**после** стриминга (чтобы плейсхолдер не разорвало между чанками) — и адрес **оборачивается в
inline-code** entity. Entity строится явно по оффсетам в уже-сконвертированном тексте (`_code_entities_for`); инъекция backticks намеренно избегается — на длинных сообщениях с эмодзи telegramify-markdown сдвигает оффсеты code-span'ов, чтобы Telegram показал его моноширинно с копированием в один тап.
См. `_send_text` / `stream_graph` в [`src/agent/stream.py`](../src/agent/stream.py). Публичная
`send_formatted(bot, chat_id, text)` — тот же рендер без подстановки, используется вебхуком для
уведомлений о входящих письмах.

### Markdown → entities

Агент пишет обычный Markdown; в [`stream.py`](../src/agent/stream.py) он конвертируется в
`(plain_text, MessageEntities)` через `telegramify-markdown` и отправляется с `entities=`
(**без** `parse_mode` — они взаимоисключающие, а entities избавляют от хрупкого
MarkdownV2-экранирования). Длинные сообщения режутся по лимиту 4096 UTF-16 код-юнитов; при любом
сборе форматирования остаётся fallback на plain text.

### Reducer `booking_field`

Поля брони в `EmailState` (`hotel_name`, `booking_ref`, `from_date`, `to_date`, `hotel_email`,
`guests`, `hotel_language`) используют редьюсер «keep existing when update is `None`». Это позволяет
агенту вызывать `set_booking_info` с любым подмножеством полей за один `Command(update=...)`, а
пропущенные (`None`) оставить нетронутыми — вместо того чтобы затирать их. Обязательных полей шесть
(всё кроме `booking_ref`); `missing_booking_fields` проверяет именно их.
