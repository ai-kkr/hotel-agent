# Spec: local-run

## Purpose

Локальный run-harness для энд-ту-энд прогона агента на машине разработчика: стаб-адаптеры почты,
локальный Docker-стек зависимостей (Temporal + PostgreSQL) и единый entrypoint, запускающий worker
и FastAPI в одном процессе без обращений к внешним сервисам.

## Requirements

### Requirement: Стаб-провайдер почты для локального режима

Система SHALL предоставлять значение конфигурации `KKR_MAIL_PROVIDER=stub`, при котором outbound-gateway не выполняет
HTTP-запросов во внешние сервисы, а складывает каждое отправленное письмо в инспектируемый in-memory буфер, сохраняя
при этом контракт `OutboundMailGateway` (включая идемпотентность по `idempotency_key`).

#### Scenario: Исходящее письмо не уходит в сеть
- **WHEN** activity вызывает `gateway.send(...)` при `KKR_MAIL_PROVIDER=stub`
- **THEN** система НЕ выполняет ни одного исходящего HTTP-запроса
- **AND** письмо добавляется в локальный буфер исходящих (`outbox`) с полями `to`, `subject`, `body`, `booking_id`,
  `idempotency_key`

#### Scenario: Идемпотентность сохраняется в стаб-режиме
- **WHEN** `gateway.send(...)` вызывается повторно с тем же `idempotency_key` (результат activity retry)
- **THEN** система не добавляет дубликат письма в буфер
- **AND** возвращает тот же `message_id`, что и при первом вызове

#### Scenario: Стаб-режим не влияет на прод-конфигурацию
- **WHEN** `KKR_MAIL_PROVIDER` не задан или равен `mailgun`
- **THEN** система использует `MailgunOutboundGateway` (поведение без изменений)

### Requirement: Inbound-нормализатор без проверки подписи для локального режима

Система SHALL предоставлять inbound-нормализатор для `stub`-провайдера, который парсит поля webhook-пэилоуда
(`sender`/`from`, `recipient`/`to`, `subject`, `body-plain`/`stripped-text`, `Date`/`date`, `Message-Id`) в
доменное событие `InboundEmail`, не требуя валидной HMAC-подписи.

#### Scenario: Локальная эмуляция входящего письма
- **WHEN** на `/webhooks/stub/inbound` (или через прямой вызов normalizer) поступает пэйлоад с полями `from`, `subject`,
  `body-plain` без подписи
- **THEN** система нормализует его в `InboundEmail` с корректными `sender`, `subject`, `body`, `received_at`

### Requirement: Локальный Docker-стек зависимостей

Система доставки SHALL включать декларативный Docker-compose файл, поднимающий Temporal Server (с UI) и PostgreSQL
одной командой, достаточный для локального запуска агента.

#### Scenario: Подъём зависимостей одной командой
- **WHEN** разработчик выполняет `docker compose up` в корне репозитория
- **THEN** поднимаются Temporal Server (доступен по адресу из `KKR_TEMPORAL_TARGET`), Temporal Web UI и PostgreSQL
  (доступный по DSN из `KKR_POSTGRES_DSN` / `KKR_LANGGRAPH_DSN`)

#### Scenario: Очистка локального стека
- **WHEN** разработчик выполняет `docker compose down -v`
- **THEN** все локальные сервисы и их тома удаляются без влияния на другие окружения

### Requirement: Единый локальный entrypoint

Система SHALL предоставлять единый entrypoint, который по локальной конфигурации (`.env`) собирает Temporal
клиент + worker, LangGraph-агентов, стаб-почтовые адаптеры и FastAPI-приложение, и запускает Temporal worker и
uvicorn в одном процессе.

#### Scenario: Локальный запуск одной командой
- **WHEN** разработчик выполняет команду локального запуска (например, `uv run python main_local.py`) при поднятом
  docker-стеке
- **THEN** в одном процессе стартуют Temporal worker (зарегистрированы `BookingWorkflow` + `ConciergeActivities`) и
  FastAPI-приложение с подключёнными `webhook_deps`
- **AND** webhook-зависимости используют стаб-адаптеры (без обращений к Mailgun)

#### Scenario: Локальная прогонка полного конвейера
- **WHEN** в локально запущенное приложение поступает эмулированный inbound (через стаб-normalizer)
- **THEN** событие доходит до `BookingWorkflow`, исполняются activity, агенты отрабатывают turn, а исходящее письмо
  попадает в стаб-outbox (без внешних HTTP-вызовов)

### Requirement: Конфигурация и документация локального режима

Репозиторий SHALL содержать `.env.example` со всеми переменными окружения локального режима и документацию с пошаговой
инструкцией запуска.

#### Scenario: Разработчик впервые поднимает локальное окружение
- **WHEN** разработчик копирует `.env.example` в `.env`, выполняет `docker compose up`, применяет миграции и запускает
  локальный entrypoint
- **THEN** приложение готово принимать webhook-и и исполнять workflow в локальном режиме

#### Scenario: Документация описывает локальный режим
- **WHEN** разработчик открывает `docs/ops.md`
- **THEN** там присутствует раздел «Локальный запуск» с переменными окружения, командами docker и entrypoint, а также
  описанием стаб-outbox и альтернативой `temporal server start-dev`
