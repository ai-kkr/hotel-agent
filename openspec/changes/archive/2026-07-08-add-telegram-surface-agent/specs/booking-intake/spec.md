## ADDED Requirements

### Requirement: Чат-shaped intake наравне с email
Система SHALL принимать бронь не только через email-forward на `c.<token>@`, но и через
chat-shaped событие от surface-агента (переданный в чат payload подтверждения + cover-text
пожелания), и SHALL обрабатывать его тем же `IntakeService` и тем же экстрактором, что и
email-путь.

#### Scenario: Чат-forward и email-forward дают одинаковый результат
- **WHEN** одинаковое подтверждение поступает через чат-forward и через email-forward одного
  клиента
- **THEN** оба пути производят эквивалентный `ExtractedBooking` и стартуют workflow идентично

#### Scenario: Делегирование экстракции ядру
- **WHEN** surface-агент получает подтверждение в чате
- **THEN** он делегирует извлечение в общий экстрактор и `IntakeService`, не дублируя логику
  извлечения

### Requirement: Ослабленная sender-аутентификация для chat-origin клиентов
Для клиентов, чья идентичность установлена через `ChannelSession` (chat-origin), система SHALL
аутентифицировать intake по сессии канала, а не по SPF/DKIM отправителя, поскольку их приватный
mailbox `c.<token>@` никогда не раскрывается и служит секретным identity-якорем. Email-channel
клиенты SHALL по-прежнему проходить строгую SPF/DKIM-проверку отправителя без изменений.

#### Scenario: Chat-origin intake без SPF/DKIM
- **WHEN** chat-origin клиент инициирует intake через чат-сессию
- **THEN** intake выполняется от имени этого клиента без требования совпадения email-отправителя

#### Scenario: Email-channel клиент — строгая проверка сохранена
- **WHEN** email-channel клиент шлёт forward на `c.<token>@`
- **THEN** система по-прежнему требует и проверяет совпадение отправителя с зарегистрированным
  email клиента (без изменений)
