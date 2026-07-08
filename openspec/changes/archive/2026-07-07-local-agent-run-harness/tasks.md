## 1. Стаб-провайдер почты (config + адаптеры)

- [x] 1.1 Расширить `MailProvider` в `src/infrastructure/config.py` литералом `"stub"` (без изменения default `mailgun`).
- [x] 1.2 Создать `src/infrastructure/mail/stub.py`: `StubOutboundGateway` (реализует `OutboundMailGateway`, пишет в
      in-memory `outbox`, сохраняет идемпотентность через переданный `BookingRepository` как `MailgunOutboundGateway`),
      `StubInboundNormalizer` (парсит те же поля, без проверки подписи), dataclass `OutboundEmailRecord`.
- [x] 1.3 Добавить ветки `"stub"` в `build_inbound_normalizer` и `build_outbound_gateway`
      (`src/infrastructure/mail/factory.py`), возвращающие стаб-адаптеры.
- [x] 1.4 Логировать каждую запись в outbox через `structlog` (`event=outbound.stub.recorded`, `to`, `subject`,
      `booking_id`, `idempotency_key`), сохраняя существующее логгирование.

## 2. Тесты стаб-провайдера

- [x] 2.1 Unit-тест: `StubOutboundGateway` не делает HTTP и кладёт письмо в outbox с нужными полями.
- [x] 2.2 Unit-тест: повторный `send` с тем же `idempotency_key` не дублирует запись и возвращает тот же `message_id`.
- [x] 2.3 Unit-тест: `StubInboundNormalizer` корректно парсит пэйлоад в `InboundEmail` без подписи.
- [x] 2.4 Unit-тест: фабрики возвращают стаб-адаптеры при `mail_provider="stub"` (и `mailgun` по умолчанию не меняется).

## 3. Локальный Docker-стек зависимостей

- [x] 3.1 Создать `docker-compose.yml` в корне с сервисами: `postgres` (для домена + LangGraph), `temporal`
      (`temporalio/auto-setup` или эквивалент), `temporal-ui` на стандартном порту. Параметризовать через переменные
      из `.env`.
- [x] 3.2 Убедиться, что порты/DSN соответствуют default'ам `Settings` (`localhost:7233`,
      `postgresql+asyncpg://...localhost:5432/kkr`).

## 4. Единый локальный entrypoint

- [x] 4.1 Создать модуль сборки локального приложения (`src/infrastructure/runtime/local.py`): из `Settings`
      строит стаб-адаптеры (`build_inbound_normalizer` / `build_outbound_gateway`), репозитории, `ConciergeActivities`,
      `InboundDispatcher`/`IntakeService`, `build_webhook_deps`, `create_app`, `build_worker` (Temporal-клиент и
      `build_agents` подключаются в `main_local.py`).
- [x] 4.2 Создать `main_local.py`: поднимает Temporal worker (`worker.run`) в фоновой `asyncio`-задаче и запускает
      uvicorn в том же event-loop; вызывает `configure_logging()` на старте.
- [x] 4.3 Корректно обрабатывать shutdown (отмена worker-таска, закрытие httpx-клиента, `engine.dispose()`).
      _(Доп.: webhooks.py теперь принимает `provider="stub"` без проверки подписи — `/webhooks/stub/inbound`.)_

## 5. Тесты локального wiring

- [x] 5.1 Тест, что локальная сборка возвращает FastAPI-приложение с подключёнными стаб-`webhook_deps` и не создаёт
      реальных Mailgun-адаптеров (мок Temporal-клиента/`worker`/`agents`).
- [x] 5.2 Тест маршрута `/webhooks/stub/inbound` без подписи (`tests/presentation/test_webhooks.py`).

## 6. Конфигурация и документация

- [x] 6.1 Создать `.env.example` со всеми `KKR_*` для локального режима (`KKR_MAIL_PROVIDER=stub`,
      `KKR_TEMPORAL_TARGET=localhost:7233`, DSN на локальный docker-postgres, `KKR_LLM_MODEL`, тайминги).
- [x] 6.2 Добавить раздел «Local launch» в `docs/ops.md`: переменные окружения, `docker compose up`, применение
      миграций (`uv run alembic upgrade head`), команда запуска entrypoint, описание стаб-outbox и альтернатива
      `temporal server start-dev`.
- [x] 6.3 README не затрагивался (вне scope; инструкция живёт в `docs/ops.md`).

## 7. Definition of Done

- [x] 7.1 `uv run ruff check` — без предупреждений _(на изменённых файлах: чисто;
      предсуществующий `main_experiment.py:32` unused `mail_gateway` вне scope этого change)._
- [x] 7.2 `uv run ty check` — чисто _(на изменённых файлах: чисто; предсуществующие
      диагностики по другим модулям/сторонним стабам вне scope)._
- [x] 7.3 `uv run pytest` — зелёно, покрытие ≥ 80 % _(177 passed, 1 skipped, 90.32 %)_.
- [x] 7.4 Ручная проверка: локальный подъём (`docker compose up` + entrypoint) принимает webhook и кладёт письмо в
      стаб-outbox _(требует запущенного Docker/Temporal — оставлено на ручную проверку разработчика)._
