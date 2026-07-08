# Tasks: add-concierge-agent

План реализации. Группы упорядочены по зависимостям (снизу вверх по Clean Architecture:
domain → infrastructure → presentation, затем агенты/воркфлоу, затем сквозные интеграции и ops).

Трассировка групп → capability (см. `specs/`):
- Группы 4, 7 → `messaging-gateway`, `booking-intake`
- Группы 5, 6 → `hotel-negotiation`
- Группа 8 → `client-communication`
- Группа 9 → сквозные (все capability)

**Принципы из конституции (`openspec/project.md`):** TDD (тесты сначала, покрытие ≥80%); миграции
для любых изменений БД; не удалять error handling/логирование; DoD — `ruff check`, `ty check`,
`uv run pytest` все зелёные.

## 1. Bootstrap & конфигурация

- [x] 1.1 Инициализировать uv-проект, `pyproject.toml`; зафиксировать runtime и добавить зависимости: fastapi, uvicorn, sqlalchemy, alembic, asyncpg, temporalio, langgraph, langgraph-checkpoint-postgres, pydantic v2, httpx, structlog.
- [x] 1.2 Настроить DoD-инструменты: `ruff`, `ty`, `pytest` (конфиги в `pyproject.toml`).
- [x] 1.3 Создать скелет Clean Architecture: `src/domain`, `src/infrastructure`, `src/presentation`, `tests/`.
- [x] 1.4 Слой конфигурации (pydantic-settings): выбор mail-провайдера, ключи Mailgun, Temporal target, Postgres DSN, домен `kkr-hotel.com`, таймаут/лимит follow-up, порог confidence извлечения.
- [x] 1.5 Базовые доменные идентификаторы: `BookingId`, `ClientToken`, `TopicId`, `EmailAddress`, `LocalPart`.

## 2. Domain layer (чистый, без I/O)

- [x] 2.1 Сущности: `Client`, `Booking`, `Topic` (early-checkin / room-upgrade / wish-derived), `Message`, `HotelContact`. Тесты на инварианты.
- [x] 2.2 Value objects и статусы: `TopicStatus` (OPEN/RESOLVED/UNRESOLVED/CAN'T_PROGRESS), `BookingLifecycle`.
- [x] 2.3 Доменные события: `ConfirmForward`, `HotelReply`, `ClientMessage`.
- [x] 2.4 Модель интентов агента: `SendEmail`, `NeedMoreInfo`, `Resolved`, `SearchDone` (агент → интент, без side-effects).
- [x] 2.5 Порты (интерфейсы) в domain: `OutboundMailGateway`, `InboundMailNormalizer`, `ClientNotifier`, `BookingRepository`, `HotelDirectoryRepository`, и суженные агентские порты `ConfirmationExtractor`, `ContactDiscoverer`, `NegotiationAgent`, `ReportBuilder`.

## 3. Persistence (Postgres)

- [x] 3.1 SQLAlchemy-модели под доменные сущности.
- [x] 3.2 Alembic: начальная миграция схемы (миграциями, не «вживую»).
- [x] 3.3 Репозитории (`BookingRepository` и др.) + маппинг domain↔ORM.
- [x] 3.4 Подготовить схему под LangGraph `PostgresSaver` (`thread_id = booking_id`).
- [x] 3.5 Тесты репозиториев.

## 4. Messaging gateway (`messaging-gateway`)

- [x] 4.1 `OutboundMailGateway` (порт) + `MailgunOutboundGateway` (send API).
- [x] 4.2 Идемпотентная отправка: ключ `booking_id:step`; отсутствие дубля при ретрае активити.
- [x] 4.3 `InboundMailNormalizer` (порт) + `MailgunWebhookNormalizer` → доменные события по local-part + `From`.
- [x] 4.4 Верификация подписи Mailgun-вебхука; отказ при неверной подписи.
- [x] 4.5 Фабрика адаптеров по конфигу (Mailgun по умолчанию; слот под Custom/других).
- [x] 4.6 FastAPI-эндпоинты `/webhooks/{provider}/inbound` и `/webhooks/{provider}/status` (per-provider).
- [x] 4.7 Dispatcher по local-part: `c.<token>` → intake; `b.<booking>` → signal `BookingWorkflow`.
- [x] 4.8 Тесты: нормализация, верификация подписи, идемпотентность, диспатч.

## 5. LangGraph-агенты (`hotel-negotiation`, мозг)

- [x] 5.1 `ConfirmationExtractor`-субграф: structured output (поля брони), валидация, confidence; разделение обложки клиента и forwarded-блока → пожелания.
- [x] 5.2 Тулы агента (только чтение): `web_search`, `fetch_url`, `recall_booking`/`read_history`.
- [x] 5.3 `ContactDiscoverer`-субграф: поиск контакта отеля + определение языка (fallback EN).
- [x] 5.4 `NegotiationAgent`-граф (per-booking thread): событие → ReAct-цикл (LLM + tools) → эмиссия интента; **без** тула отправки email.
- [x] 5.5 `ReportBuilder`-субграф: сводка результатов по темам.
- [x] 5.6 Подключить `PostgresSaver` как checkpoint saver; `thread_id = booking_id`.
- [x] 5.7 Валидация/парсинг интентов; low-confidence → `NeedMoreInfo`.
- [x] 5.8 Тесты графов: structured output, эмиссия интентов, fallback языка.

## 6. Temporal workflows (durable spine)

- [x] 6.1 Temporal worker, регистрация активити.
- [x] 6.2 Активити: `extract`, `discover_contact`, `agent_turn`, `send_email` (через gateway), `build_report`, `relay_to_client`, `update_booking_state`. **Все LLM-вызовы — только внутри активити.**
- [x] 6.3 `BookingWorkflow` (`workflow_id = booking_id`): extract → discover → цикл разговора → build_report → `await client_followup` → реактивация.
- [x] 6.4 Сигналы `on_hotel_reply`, `client_followup`; таймер таймаута ответа отеля.
- [x] 6.5 Follow-up по таймауту с лимитом повторов; переходы UNRESOLVED / CAN'T_PROGRESS.
- [x] 6.6 Обработка delivery-status (BOUNCE → переоценка контакта / CAN'T_PROGRESS).
- [x] 6.7 Детерминизм воркфлоу: LLM только в активити; тест на replay-совместимость.
- [x] 6.8 Интеграционные тесты воркфлоу (мок агента/gateway).

## 7. Booking intake (`booking-intake`)

- [x] 7.1 Разрешение клиента по токену + SPF/DKIM проверка отправителя; отказ при несовпадении.
- [x] 7.2 Старт `BookingWorkflow` по `ConfirmForward`; инициализация дефолтных тем (early-checkin, room-upgrade) в OPEN.
- [x] 7.3 Разбор пожеланий из обложки (через `ConfirmationExtractor`) → дополнительные темы.
- [x] 7.4 Маршрутизация unknown-token / unauthorized → reject.
- [x] 7.5 Тесты intake.

## 8. Client communication (`client-communication`)

- [x] 8.1 `ClientNotifier` (порт) + email-адаптер (через messaging-gateway).
- [x] 8.2 Доставка отчёта клиенту по настроенному каналу.
- [x] 8.3 Приём фоллоу-апа: email-реплай на `b.<booking>` → `ClientMessage` → signal `client_followup`.
- [x] 8.4 API `POST /api/client-message` → `ClientMessage` → signal.
- [x] 8.5 Структура под омиканальность: слоты адаптеров (Telegram/WhatsApp/native) без правок ядра intake/negotiation.
- [x] 8.6 Тесты доставки, приёма фоллоу-апа и реактивации контекста.

## 9. End-to-end интеграции

- [x] 9.1 E2E: форвард подтверждения → переговоры → отчёт (мок отеля).
- [x] 9.2 E2E: фоллоу-ап клиента → повторный заход к отелю (мок).
- [x] 9.3 E2E: discovery контакта через веб (мок search/fetch).
- [x] 9.4 E2E: идемпотентная отправка под ретраем активити.
- [x] 9.5 E2E: язык отеля + fallback EN.

## 10. Ops, hardening, DoD

- [x] 10.1 DNS: SPF/DKIM/DMARC на `kkr-hotel.com`; MX + catch-all.
- [x] 10.2 Mailgun: catch-all route → вебхук; подпись вебхука; прогрев домена/мониторинг bounce-rate.
- [x] 10.3 Сквозное логирование и error handling на всех слоях.
- [x] 10.4 Observability Temporal (видимость воркфлоу/активити).
- [x] 10.5 DoD-гейт: `ruff check` чисто, `tycheck` чисто, `uv run pytest` зелёный; покрытие ≥80%.
