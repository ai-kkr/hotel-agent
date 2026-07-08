# Spec: messaging-gateway

## Purpose

Транспортная абстракция каналов: port-пара (inbound-normalizer + outbound-gateway) с идемпотентной
отправкой, верификацией подписи вебхука и catch-all маршрутизацией. На v1 — email/Mailgun; другие
провайдеры/каналы подключаются как адаптеры, выбор — конфигурацией.
## Requirements
### Requirement: Контракт нормализации inbound
Система SHALL нормализовать входящие канальные события (например, вебхук Mailgun) в доменные
события (ConfirmForward, HotelReply, ClientMessage) через per-provider normalizer.

#### Scenario: Вебхук Mailgun
- **WHEN** поступает валидный inbound-вебхук Mailgun
- **THEN** система нормализует его в соответствующее доменное событие

#### Scenario: Неверная подпись вебхука
- **WHEN** подпись вебхука не проходит верификацию
- **THEN** система отклоняет запрос

### Requirement: Контракт отправки outbound
Система SHALL отправлять исходящие сообщения через provider-gateway за портом, развязанно от логики
negotiation и client-communication.

#### Scenario: Отправка через провайдера
- **WHEN** воркфлоу эмитит исходящее сообщение
- **THEN** оно отправляется через настроенного провайдера (Mailgun на v1)

### Requirement: Идемпотентная отправка
Система SHALL отправлять каждое исходящее ровно один раз на логический шаг, используя
детерминированный idempotency-key, в том числе при ретраях активити.

#### Scenario: Ретрай на границе отправки
- **WHEN** активити отправки ретраится после таймаута на границе отправки
- **THEN** дубликат письма не создаётся (отправка ровно одна)

### Requirement: Переключаемость провайдера
Система SHALL выбирать почтового провайдера (и будущие каналы) конфигурацией, с Mailgun как
значением по умолчанию на v1; добавление провайдера эквивалентно добавлению адаптера.

#### Scenario: Смена провайдера конфигом
- **WHEN** конфигурация переключает провайдера
- **THEN** inbound и outbound используют новый адаптер без изменения ядра

### Requirement: Catch-all маршрутизация
Система SHALL принимать catch-all адресное пространство `*@kkr-hotel.com` и SHALL диспетчеризовать
по local-part: `c.<token>` направляет в intake, `b.<booking_id>` направляет как сигнал в
BookingWorkflow(booking_id).

#### Scenario: Маршрутизация intake
- **WHEN** входящее письмо адресовано на `c.<token>@`
- **THEN** оно направляется в intake

#### Scenario: Маршрутизация разговора
- **WHEN** входящее письмо адресовано на `b.<booking_id>@`
- **THEN** оно направляется как сигнал в BookingWorkflow(booking_id)

### Requirement: Извлечение тела письма с HTML-fallback
Normalizer inbound-события SHALL формировать текстовое тело письма (`InboundEmail.body`),
предпочитая plaintext-часть провайдера, и SHALL fallback-ить на HTML-часть с конвертацией в текст,
когда plaintext пуст. Порядок источников: `body-plain` → `stripped-text` → `html2text(body-html)`
→ `html2text(stripped-html)`. Конвертация SHALL выполняться единой утилитой и SHALL быть
толерантной к некорректному HTML (не ронять inbound при ошибке конвертации).

#### Scenario: Письмо с plaintext-частью
- **WHEN** inbound-событие содержит непустой `body-plain` (или `stripped-text`)
- **THEN** система использует plaintext как тело без обращения к HTML-части

#### Scenario: HTML-only письмо
- **WHEN** plaintext-часть пуста, но присутствует `body-html` (или `stripped-html`)
- **THEN** система конвертирует HTML в текст и использует его как тело письма

#### Scenario: Multipart с обеими частями
- **WHEN** присутствуют и plaintext, и HTML
- **THEN** система использует plaintext (HTML не конвертируется)

#### Scenario: Некорректный HTML
- **WHEN** HTML-часть присутствует, но не конвертируется (битый HTML)
- **THEN** система не роняет обработку inbound, а оставляет best-effort результат (пустое тело или
частичный текст) — экстрактор корректно обработает low-confidence по существующему контракту
booking-intake

