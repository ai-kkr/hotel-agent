## Context

Сегодня весь wiring прод-стека собран в `main_experiment.py`: он жёстко конструирует `MailgunOutboundGateway`
(реальные HTTP-вызовы в Mailgun) и подключается к Temporal. Локально это неработоспособно: нет ключей Mailgun,
нет поднятого Temporal, нет единой команды «поднять и запустить». При этом архитектурные швы уже есть:

- `MailProvider = Literal["mailgun", "custom"]` в `config.Settings` и фабрики
  `build_inbound_normalizer` / `build_outbound_gateway` (`infrastructure/mail/factory.py`) — добавление провайдера
  это конфиг + новый модуль адаптера, без правок домена (D8).
- `OutboundMailGateway` / `InboundMailNormalizer` — protocols в `domain/ports.py`; стаб реализует тот же контракт.
- `run_worker` (`infrastructure/workflows/worker.py`) уже умеет строить Temporal worker от `Settings`.
- `build_agents` (`infrastructure/agents/factory.py`) строит четырёх агентов от `BaseChatModel` + checkpointer.

Ограничения (из `openspec/project.md`): зависимости только через `uv`/`pyproject.toml`; Clean Architecture
(направление зависимостей внутрь); TDD/покрытие ≥ 80 %; `ruff`/`ty`/`pytest` зелёные (DoD).

## Goals / Non-Goals

**Goals:**

- Локально запускать **полный конвейер** (FastAPI webhook → intake → Temporal workflow → activities → LangGraph-агенты)
  одной командой, без реального Mailgun.
- Mailgun заменён **стаб-провайдером**: отправленные письма не уходят в сеть, а попадают в инспектируемый буфер;
  inbound-вебхук принимается без проверки подписи (удобно для ручной/скриптовой эмуляции входящих писем).
- Temporal (и Postgres как его и доменная БД) поднимаются в **Docker** одной командой.
- Поведение прод-режима (`mailgun`) не меняется; стаб активируется только конфигурацией.

**Non-Goals:**

- Полноценный mock SMTP-сервер (как Mailpit) — out of scope; стаб копит письма в памяти процесса, не принимает
  реальных SMTP-соединений. (Можно добавить позже как отдельный `custom`-адаптер.)
- Реальная отправка во внешние каналы (Telegram/WhatsApp) — не относится к локальному режиму.
- CI-окружение и прод-deploy — не рассматривается; только локальная разработка/отладка.
- Эмуляция поведения LLM без ключа (LLM по-прежнему требует `OPENAI_API_KEY` через существующий wiring агентов).

## Decisions

### D1. Стаб как новое значение `mail_provider`, а не флаг окружения

**Решение:** расширить `MailProvider` литералом `"stub"` и добавить ветки в `build_inbound_normalizer` /
`build_outbound_gateway`. Активация — `KKR_MAIL_PROVIDER=stub`.

**Альтернатива:** отдельный булевый флаг `KKR_STUB_MAIL`. Отклонено — дублирует существующий механизм выбора
провайдера и ломает единый контракт «провайдер = значение конфига» (D8). `"custom"` сейчас кидает
`NotImplementedError`; `stub` закрывает именно локальный случай (без HTTP-мока конкретного вендора).

### D2. Стаб хранит исходящие письма в инспектируемом буфере

**Решение:** `StubOutboundGateway` реализует `OutboundMailGateway`, использует переданный `BookingRepository` для
той же идемпотентности (запись `Message` до «отправки», как в `MailgunOutboundGateway`), но вместо HTTP кладёт копию
письма во внутренний `list[OutboundEmailRecord]`. Буфер читается из процесса (в будущем — мини-эндпоинт `/debug/outbox`
или лог).

**Альтернатива:** писать во внешний файл/Mailpit. Отклонено на первом этапе — in-memory буфер проще, достаточно для
локальной отладки, и не добавляет зависимостей. Реальная идемпотентность (через репозиторий) проверяется так же,
как в проде.

### D3. Inbound-стаб не проверяет подпись

**Решение:** `StubInboundNormalizer` парсит те же поля, что `MailgunWebhookNormalizer` (`sender`/`from`, `subject`,
`body-plain`, `recipient`/`to`, `Date`), но без HMAC-проверки. Это позволяет слать webhook локально curl'ом/скриптом
для эмуляции входящего письма отеля/клиента.

### D4. Docker: Temporal + Postgres + UI одним compose-файлом

**Решение:** корневой `docker-compose.yml` (или `deploy/local/docker-compose.yml`) с сервисами:

- `postgres` (один инстанс для доменных таблиц и LangGraph-checkpoint; DSN-ы из `.env` уже параметризованы),
- `temporal` (+ зависимости Temporal — теоретически тот же Postgres; используем официальный образ
  `temporalio/auto-setup` для локального one-shot, чтобы не настраивать схему вручную),
- `temporal-ui` на стандартном порту.

**Альтернатива:** `temporal` через CLI-DEV-server (`temporal server start-dev`). Допустимо как более лёгкий вариант;
в compose используем docker-образ для воспроизводимости, но в документации упоминаем `start-dev` как ещё более лёгкий
путь без Docker. Решение: docker-compose как primary (соответствует требованию пользователя «temporal можно запускать в
docker»), `start-dev` — как альтернатива в docs.

### D5. Единый локальный entrypoint поднимает API + worker в одном процессе

**Решение:** `main_local.py` (или `infrastructure/runtime/local.py` + тонкий `scripts/run_local.py`) собирает:
`Settings` ← `.env`; Temporal-клиент (`worker.build_client`); LangGraph-агенты
(`build_agents` с `InMemorySaver` для локального simplicity или `PostgresSaver` из `.env`); стаб-адаптеры
(`build_inbound_normalizer`/`build_outbound_gateway`); `ConciergeActivities`; `InboundDispatcher`/`IntakeService`;
FastAPI-приложение (`create_app + build_webhook_deps`). Затем запускает Temporal worker (в фоновой `asyncio`-задаче)
и uvicorn в том же event-loop.

**Альтернатива:** два процесса (API отдельно, worker отдельно) как в проде. Отклонено для локального режима —
один процесс проще отлаживать и перезапускать; прод-wiring (`main_experiment.py`) не трогается.

### D6. Конфигурация через `.env.example`

**Решение:** добавить `.env.example` со всеми `KKR_*` для локального режима (`KKR_MAIL_PROVIDER=stub`,
`KKR_TEMPORAL_TARGET=localhost:7233`, DSN-ы на локальный docker-postgres, `KKR_LLM_MODEL` и т.д.). Не коммитим
`.env`.

## Risks / Trade-offs

- **[Один процесс маскирует прод-специфику]** → локальный one-process отличается от прод two-process; Mitigation:
  явное предупреждение в docs + сохранение `main_experiment.py` как референса прод-wiring; E2E-тесты
  (`KKR_E2E_TEMPORAL=1`) продолжают проверять реальный workflow.
- **[Стаб не ловит ошибки Mailgun-специфики]** → подпись/HMAC/формат ответа Mailgun не тестируются через стаб;
  Mitigation: существующие тесты `test_mailgun_adapters.py` / `test_mail_signature.py` покрывают Mailgun-путь отдельно.
- **[Temporal `auto-setup` тяжеловатен]** → образ поднимает свою БД; Mitigation: документируем `temporal server
  start-dev` как лёгкую альтернативу без Docker.
- **[In-memory outbox теряется при рестарте]** → приемлемо для локальной отладки; Mitigation: логирование каждого
  «отправленного» письма через `structlog` (`event=outbound.stub.recorded`), чтобы состояние было видно в логах.
- **[Новые значения конфига]** → `MailProvider` расширяется; Mitigation: не breaking — default остаётся `mailgun`.

## Migration Plan

1. Расширить `MailProvider` и фабрики (`stub` ветки) — прод-путь не меняется.
2. Добавить `docker-compose.yml`, `.env.example`, локальный entrypoint.
3. Документация (`docs/ops.md`): раздел «Локальный запуск».
4. Откат — удаление новых файлов/значений; прод работает без них.

## Open Questions

- Нужен ли мини-эндпоинт `/debug/outbox` для чтения стаб-буфера из браузера, или достаточно логов?
  (Текущее решение: логи на первом этапе, эндпоинт — по запросу.)
- Использовать ли для LangGraph локально `InMemorySaver` (быстрее, без таблиц) или `PostgresSaver` (ближе к проду)?
  (Текущее решение: по умолчанию `PostgresSaver` против локального docker-postgres, чтобы поведение было
  максимально близко к прод-чекпойнту; `InMemorySaver` — опция.)
