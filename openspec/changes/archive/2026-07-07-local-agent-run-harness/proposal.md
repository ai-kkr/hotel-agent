## Why

Запускать и отлаживать агента локально сегодня невозможно без полного прод-стека: `main_experiment.py` жёстко собирает
`MailgunOutboundGateway` (нужны реальный Mailgun API-key и рабочий `mail_domain`) и `TemporalWorkflowGateway`, а единого
способа поднять Temporal/Postgres и стартовать API + worker + агентов одной командой нет. Разработчику нужен локальный
режим, где Mailgun заменён заглушкой (письма не уходят наружу, а копятся для инспекции), Temporal поднимается в Docker,
а весь конвейер (webhook → intake → workflow → activity → агент) управляемо прогоняется на машине разработчика.

## What Changes

- Добавлен **стаб-провайдер почты** (`mail_provider = "stub"`): outbound-gateway не выполняет HTTP-запросов, а
  складывает отправленные письма в in-memory/inspectable буфер; inbound-normalizer принимает те же поля, что и Mailgun,
  но без проверки подписи. Выбор — конфигурацией (`KKR_MAIL_PROVIDER=stub`), без правок домена.
- Добавлен **локальный Docker-стек** (`docker-compose`/compose-файл), поднимающий Temporal Server + UI (+ Postgres,
  необходимый и для домена, и для LangGraph `PostgresSaver`) одной командой.
- Добавлен **единый entrypoint локального запуска** (`scripts/` или `main_local.py`), собирающий `Settings` с
  локальным `.env`, Temporal-клиент/worker, агентов (LangGraph) и стаб-адаптеры, и поднимающий одновременно
  FastAPI + Temporal worker в одном процессе.
- Добавлены **`.env.example` и документация** (`docs/ops.md` / новый раздел) с шагами запуска и переменными окружения
  для локального режима.
- Существующий `main_experiment.py` остаётся как есть (он — прод/экспериментальный wiring); локальный режим —
  отдельная обвязка.

## Capabilities

### New Capabilities

- `local-run`: обвязка для локального запуска и отладки агента — стаб-провайдер почты, docker-стек зависимостей
  (Temporal/Postgres), единый entrypoint (API + worker + агенты) и конфигурация/документация для разработчика.

### Modified Capabilities

_(нет — выбор mail-провайдера через конфиг уже предусмотрен в `messaging-gateway`; добавляется новое значение
`stub`, что не меняет requirement-уровневый контракт, только расширяет реализацию адаптера.)_

## Impact

- **Код**: `src/infrastructure/config.py` (расширить `MailProvider` литералом `"stub"`); новый модуль
  `src/infrastructure/mail/stub.py` (`StubOutboundGateway`, `StubInboundNormalizer`) + ветки в
  `src/infrastructure/mail/factory.py`; новый `src/infrastructure/runtime/local.py` (или `main_local.py`) для сборки
  приложения и worker'а; `scripts/run_local.*` для запуска.
- **Инфраструктура**: новый `docker-compose.yml` (+ директория `deploy/local/` при необходимости) с сервисами
  temporal/postgres/ui; `.env.example`.
- **Зависимости**: новых runtime-зависимостей не добавляется (Temporal/docker уже доступны; Postgres-драйверы есть).
- **Документация**: `docs/ops.md` — раздел «Локальный запуск»; `README.md` при необходимости.
- **Тесты**: unit-тесты на стаб-адаптеры и локальный wiring (покрытие ≥ 80 % по DoD).
- **Совместимость**: не breaking — стаб активируется только при `KKR_MAIL_PROVIDER=stub`; прод-поведение по умолчанию
  (`mailgun`) не меняется.
