# Эксплуатация

Операционные нюансы текущей версии: рантайм-процесс, логирование, настройка Mailtrap
(отправка, inbound-webhook, личные ящики), Alembic и локальный dev-стек. Архитектура — в
[architecture.md](architecture.md), настройка окружения и запуск — в [development.md](development.md),
продакшен-деплой на Railway — в [deployment.md](deployment.md).

> Документ описывает **фактическое** состояние кода в [`src/`](../src/). Прежняя версия
> (Temporal/Mailgun/`presentation.*`) более не используется.

## Рантайм-процесс

Один процесс: `uvicorn` поднимает FastAPI-приложение, а в его `lifespan` запускается long-polling
Telegram-бота ([`src/app/factory.py`](../src/app/factory.py)). FastAPI обслуживает inbound-webhook
Mailtrap (`POST /send_test_email`). Polling и вебхук живут вместе — это нормально для текущей
версии; в продакшене при необходимости их можно разделить.

Важно: один bot-token может опрашиваться только одним процессом (Telegram отклоняет конкурирующие
`getUpdates`).

## Логирование

Структурированный лог через `structlog` ([`src/logging.py`](../src/logging.py)): `configure_logging()`
вызывается при первом `get_logger()`. Renderer — `ConsoleRenderer` (удобно для dev). Ключевые
события с контекстом:

- `tool.*` — вызовы инструментов (`tool.set_booking_info`, `tool.send_wishes_to_hotel`,
  `tool.reply_to_hotel`, `tool.search_internet`, …) с релевантными полями;
- бот: `bot.handler_error` — исключения в обработчиках aiogram (прокидываются в лог, а не
  глотаются);
- webhook: логи приёма/разбора входящих писем и маршрутизации ответа отеля (`Received hotel
  reply`, `Received inbound event`, `Received inbound event for unknown inbox`).

## Mailtrap

Mailtrap используется и для **отправки** (Mailtrap Email API), и для **приёма** входящих
(Inbound). Один API-токен работает для обоих случаев (`KKR_MAILTRAP_API_KEY`).

### Личные ящики клиентов

При первом `/start` для гостя создаётся личный inbound-ящик
([`ClientRepository.add_client`](../src/db/repositories.py) →
[`MailtrapClient.provision_inbox`](../src/integrations/mailtrap/client.py)) внутри папки
`KKR_MAILTRAP_INBOX_ID` (`folder_id`). Адрес ящика показывается гостю — на него он пересылает
подтверждение брони. `inbox` и `inbox_id` хранятся в `clients`.

### Отправка писем

- Письма уходят через `send.api.mailtrap.io` ([`MailtrapClient.send`](../src/integrations/mailtrap/client.py)).
- **`From`** = `KKR_MAILTRAP_FROM_EMAIL` — адрес на домене, верифицированном в
  Mailtrap Email API → Sending Domains. Адрес inbound-ящика отправителем быть **не может** —
  Mailtrap вернёт `401 Unauthorized` для неверифицированного домена отправителя.
- **`Reply-To`** = inbox гостя — чтобы ответ отеля вернулся в его личный ящик и прошёл через
  webhook. Это критично для маршрутизации ответа обратно в агента.
- **В dev-режиме** (`KKR_IS_DEV=true`) письмо уходит на `user_email` гостя, а не отелю, — чтобы
  проверять отправку без реального отеля.
- Threading: ответы отелю (`reply_to_hotel`) шлются с `In-Reply-To`/`References` = последний
  `message_id` отеля и темой `Re: …` (подробно — [architecture.md](architecture.md#threading-переписки-с-отелем)).

### Inbound-webhook

Mailtrap присылает входящие письма на `POST /send_test_email`:

1. Зависимость [`verify_mailtrap_signature`](../src/app/dependencies.py) проверяет
   `Mailtrap-Signature` (HMAC по **raw**-телу запроса) секретом `KKR_MAILTRAP_SIGNING_SECRET`.
   Несовпадение → HTTP 401.
2. По `inbox_id` события находится клиент; для каждого события через `get_message` забирается
   полное тело письма.
3. **Маршрутизация** ([`src/app/webhook.py`](../src/app/webhook.py)):
   - если `In-Reply-To` письма совпадает с записью в `outbound_emails` — это **ответ отеля**: в
     state агента кладутся `last_hotel_message_id` / `last_hotel_subject`, в чат гостя шлётся
     уведомление «🏨 **Ответ отеля**» (отправитель + тема), и агенту подаётся ход
     `hotel reply:\n<body>`;
   - иначе — **пересланное письмо гостя**: адрес отправителя привязывается к клиенту (если ещё
     не привязан), письмо сохраняется, в чат шлётся уведомление «📨 **Новое письмо**»
     (отправитель + тема + «приступаю к обработке»), и агенту подаётся ход
     `forwarded email:\n<body>`.
   - уведомления рендерятся через `send_formatted` (Markdown → entities, без `parse_mode`);
   - дубликаты пересланных писем (по `message_id` + `client_id`) игнорируются
     (`DuplicateForwardedEmailError`).

Регистрировать URL вебхука нужно на стороне Mailtrap (он должен указывать на этот сервер).

## Alembic

Конфигурация — [`alembic/`](../alembic); metadata берётся из `src.db.base.Base`. Управляются
только таблицы, описанные в моделях; legacy-таблицы прежней версии (`bookings`, `messages` и
т. п.) не дропаются, а игнорируются (`_include_object` в [`alembic/env.py`](../alembic/env.py)).
Команды — в [development.md](development.md#миграции-схемы--alembic).

## Локальный dev-стек

[`docker-compose.yml`](../docker-compose.yml) поднимает зависимости. Для запуска приложения
локально нужны **postgres** и **temporal** (+ опционально `temporal-ui`):
`docker compose up -d postgres temporal`. Langfuse (трейсинг LLM) — опционален: интегрирован, но
выключен до явного `KKR_LANGFUSE_ENABLED=true` + ключей.

## Известные нюансы

- **Дрейф `outbound_emails.created_at`** — `alembic check` показывает расхождение NOT NULL между
  моделью и БД; правится отдельной миграцией при необходимости, на логику не влияет.
- **Пул asyncpg** — соединения защищены от «протухания» через `pool_pre_ping` + `pool_recycle`
  ([`src/db/session.py`](../src/db/session.py)). Без этого на простаивающих соединениях возможен
  `ConnectionDoesNotExistError` на `BEGIN`.
- **Состояние агента** — хранится в таблице `states` (`StateORM`), а не через LangGraph-чекпоинтер.
  Каждый ход: `AgentWorkflow` грузит `EmailState` активити `load_state`, гоняет граф с
  in-поворотным `InMemorySaver`, сохраняет результат активити `save_state`
  ([`src/temporal/activities.py`](../src/temporal/activities.py)). История переписки переживает
  рестарт процесса. Таблица `states` — обычная ORM-модель, управляется alembic
  (`20260717_1430_7c8d9e0f1a2b_add_states.py`); `checkpoint_*` таблиц (и `AsyncPostgresSaver`) больше
  нет. `/new` сбрасывает контекст удалением строки (`delete_state_by_client_id`).
- **Langfuse (опционально)** — трейсинг LLM. Включается `KKR_LANGFUSE_ENABLED=true` + обоими
  ключами (`KKR_LANGFUSE_PUBLIC_KEY`/`KKR_LANGFUSE_SECRET_KEY`, берутся из `LANGFUSE_INIT_PROJECT_*`
  в compose). Один агент-оборот = один трейс; `session_id` = per-client thread (вся переписка гостя
  группируется в сессию), `user_id` = id клиента, `trace_id` детерминированно выводится из
  `workflow.info().run_id` (стабилен при replay). Callback навешивается **поузельно** через
  [`src/agent/helpers/langfuse.py`](../src/agent/helpers/langfuse.py) (`var_child_runnable_config`);
  init/shutdown клиента — в [`src/agent/tracing.py`](../src/agent/tracing.py) (инициализируется в
  Temporal-воркере, flush — в lifespan). Без включения — no-op.
