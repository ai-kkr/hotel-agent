# Spec: client-communication

## Purpose

Клиентская сторона разговора: доставка отчётов/уведомлений клиенту и приём фоллоу-апов,
канал-независимо (email на v1; архитектурная готовность к Telegram/WhatsApp/native). Ввод клиента
унифицирован в доменное событие ClientMessage.

## Requirements

### Requirement: Канал-независимый обмен с клиентом
Система SHALL доставлять отчёты и уведомления клиенту и принимать фоллоу-апы через канальную
абстракцию, не привязанную к email-логике.

#### Scenario: Доставка через настроенный канал
- **WHEN** отчёт готов к доставке
- **THEN** он отправляется через настроенный outbound-канал (email на v1)

#### Scenario: Фоллоу-ап через любой канал
- **WHEN** клиент отвечает через любой настроенный канал
- **THEN** ввод нормализуется в ClientMessage и возобновляет разговор по брони

### Requirement: Доставка отчёта
Система SHALL доставлять сформированный отчёт клиенту как одно из событий доставки через настроенный
outbound-канал; отчёт SHALL доставляться через тот же канал-агностичный механизм доставки, что и
промежуточные события прогресса.

#### Scenario: Отчёт доставлен
- **WHEN** hotel-negotiation передал отчёт
- **THEN** client-communication доставляет его клиенту через настроенный outbound-канал как
  финальное событие прогресса

### Requirement: Приём фоллоу-апа и удержание контекста
Система SHALL принимать фоллоу-ап клиента после отчёта, SHALL маршрутизировать его на бронь и
SHALL удерживать предыдущий контекст, чтобы агент мог повторно обратиться к отелю.

#### Scenario: Реактивация разговора
- **WHEN** клиент присылает фоллоу-ап после отчёта
- **THEN** разговор по брони реактивируется с полным контекстом и может повторно обратиться к отелю

### Requirement: Омиканальная расширяемость
Система SHALL допускать добавление клиентских каналов (Telegram, WhatsApp, нативное приложение) как
адаптеров без изменения ядра intake/negotiation.

#### Scenario: Добавлен новый канал
- **WHEN** добавлен адаптер нового канала (inbound-normalizer + outbound-gateway)
- **THEN** inbound нормализуется в ClientMessage, outbound идёт через gateway, ядро intake/negotiation не меняется

### Requirement: Channel session identity
The system SHALL maintain a `ChannelSession` binding a client to a per-channel address (e.g.
Telegram `chat_id`), so that outbound delivery and inbound routing can resolve a channel address
from a client (and vice versa) without coupling to any specific channel. A client MAY have sessions
on multiple channels.

#### Scenario: Outbound resolved from client
- **WHEN** the workflow pushes an event for a client who has a channel session
- **THEN** outbound delivery uses that session's channel address

#### Scenario: Inbound resolved to client
- **WHEN** an inbound chat event arrives from a known channel address
- **THEN** the system resolves it to the owning client

### Requirement: Progress event stream
The system SHALL deliver a stream of progress events to the client over the configured channel,
pushed from the workflow on booking lifecycle/topic transitions, in addition to the final report.
Each event SHALL carry a kind, the booking id, a short title, and a body.

#### Scenario: Lifecycle transition pushed
- **WHEN** a booking transitions to a user-visible lifecycle state (e.g. contact ready, email sent,
  hotel replied)
- **THEN** the system pushes a progress event to the client's configured channel

#### Scenario: Coalesced transitions
- **WHEN** multiple transitions occur in quick succession
- **THEN** the system coalesces or summarizes them to avoid flooding the channel
