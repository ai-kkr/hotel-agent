## ADDED Requirements

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
