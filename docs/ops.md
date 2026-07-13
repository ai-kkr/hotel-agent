# Эксплуатация

Операционные нюансы текущей версии: рантайм-процесс, логирование, настройка Mailtrap
(отправка, inbound-webhook, личные ящики), Alembic и локальный dev-стек. Архитектура — в
[architecture.md](architecture.md), настройка окружения и запуск — в [development.md](development.md).

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
     state агента кладутся `last_hotel_message_id` / `last_hotel_subject`, и агенту подаётся ход
     `hotel reply:\n<body>`;
   - иначе — **пересланное письмо гостя**: адрес отправителя привязывается к клиенту (если ещё
     не привязан), письмо сохраняется, и агенту подаётся ход `forwarded email:\n<body>`.
   - дубликаты пересланных писем (по `message_id` + `client_id`) игнорируются
     (`DuplicateForwardedEmailError`).

Регистрировать URL вебхука нужно на стороне Mailtrap (он должен указывать на этот сервер).

## Alembic

Конфигурация — [`alembic/`](../alembic); metadata берётся из `src.db.base.Base`. Управляются
только таблицы, описанные в моделях; legacy-таблицы прежней версии (`bookings`, `messages` и
т. п.) не дропаются, а игнорируются (`_include_object` в [`alembic/env.py`](../alembic/env.py)).
Команды — в [development.md](development.md#миграции-схемы--alembic).

## Локальный dev-стек

[`docker-compose.yml`](../docker-compose.yml) поднимает зависимости. Для текущего кода обязателен
только **postgres** (`docker compose up -d postgres`). Прочие сервисы compose (temporal, langfuse
и их инфраструктура) сохранены на будущее — текущее приложение их не использует.

## Известные нюансы

- **Дрейф `outbound_emails.created_at`** — `alembic check` показывает расхождение NOT NULL между
  моделью и БД; правится отдельной миграцией при необходимости, на логику не влияет.
- **Пул asyncpg** — соединения защищены от «протухания» через `pool_pre_ping` + `pool_recycle`
  ([`src/db/session.py`](../src/db/session.py)). Без этого на простаивающих соединениях возможен
  `ConnectionDoesNotExistError` на `BEGIN`.
- **Чекпоинтер агента** — сейчас `MemorySaver` (в памяти, в [`src/context.py`](../src/context.py));
  история переписки не переживает рестарт процесса. Для персистентности заменить на
  `PostgresSaver` (DSN `KKR_LANGGRAPH_DSN` уже предусмотрен в настройках).
