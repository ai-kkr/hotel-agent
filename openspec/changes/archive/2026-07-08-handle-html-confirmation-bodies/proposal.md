## Why

Пересланные подтверждения брони часто приходят **только в HTML** (нет `text/plain`-части): так шлют многие отели напрямую и часть OTA. Нормализатор inbound-вебхука Mailgun читает исключительно `body-plain`/`stripped-text` и не имеет fallback на `body-html`. Для HTML-only писем `body-plain` у Mailgun пуст → экстрактор `ConfirmationExtractor` получает пустой `forwarded_payload` → бронь помечается low-confidence и клиенту уходит запрос уточнения (молчаливая деградация, не краш). Нужно закрывать эту дыру, чтобы HTML-only брони корректно извлекались.

## What Changes

- Нормализатор inbound-писем (`MailgunWebhookNormalizer` и симметричный stub) SHALL при пустом `body-plain`/`stripped-text` брать `body-html`/`stripped-html` и конвертировать HTML → текст (`html2text`), прежде чем формировать `InboundEmail.body`.
- `html2text` добавляется в основные зависимости (`[project].dependencies`), не в dev.
- HTML-конвертация живет в одной общей утилите (переиспользуется нормализатором Mailgun и stub-адаптером), без дублирования логики.
- Тесты покрывают: HTML-only тело → извлекается текст; multipart (есть `body-plain`) → `body-plain` предпочтительнее; пустой `body-plain` + `body-html` → fallback.

## Capabilities

### New Capabilities
<!-- Нет новых capability; изменяется поведение существующего messaging-gateway. -->

### Modified Capabilities
- `messaging-gateway`: нормализатор inbound-писем теперь обязан извлекать тело из HTML-части, когда plaintext-часть пуста.

## Impact

- **Код:** `src/infrastructure/mail/mailgun.py` (`MailgunWebhookNormalizer.parse`), `src/infrastructure/mail/stub.py` (симметричный inbound-парсинг); новая общая утилита HTML→text в `src/infrastructure/mail/`. Продуктовая доменная логика и экстрактор не меняются (LLM получает тот же `forwarded_payload`, только теперь непустой для HTML-only).
- **Зависимости:** `html2text` переезжает из dev в основные `[project].dependencies`.
- **Спека:** delta к `messaging-gateway` (новое требование про HTML-fallback).
- **Тесты:** расширение `tests/infrastructure/test_mailgun_adapters.py` / `test_stub_mail.py` под HTML-fallback; продуктовый coverage-gate (80%) продолжает действовать.
- **Совместимость:** поведение для писем с `body-plain` не меняется (plaintext предпочтительнее); меняется только случай пустого plaintext.
