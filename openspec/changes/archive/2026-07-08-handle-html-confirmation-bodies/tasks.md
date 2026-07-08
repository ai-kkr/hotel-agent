## 1. Зависимости

- [x] 1.1 Перенести `html2text` из `[project.optional-dependencies].dev` в `[project].dependencies` (`uv remove --optional dev html2text && uv add html2text`).
- [x] 1.2 Проверить, что `scripts/` (dev-тулза) продолжает работать с `html2text` как с основной зависимостью.

## 2. Общая утилита HTML→text (D2)

- [x] 2.1 Создать `src/infrastructure/mail/html.py` с `html_to_text(html: str) -> str` (обёртка над `html2text`: `body_width=0`, `ignore_images=True`, `errors-resilient`).
- [x] 2.2 Тест `tests/infrastructure/test_mail_html.py`: реалистичный HTML-фрагмент подтверждения (таблица с отель/даты/ref) → текст содержит ключевые поля, без тегов; битый HTML → не падает, возвращает best-effort.

## 3. Нормализатор Mailgun (D1, D4)

- [x] 3.1 В `MailgunWebhookNormalizer.parse` заменить выбор тела на общую `extract_body_text(payload)` (plaintext → fallback `html_to_text(body-html/stripped-html)`).
- [x] 3.2 Тест в `tests/infrastructure/test_mailgun_adapters.py`: HTML-only payload (`body-plain` пуст, `body-html` заполнен) → `InboundEmail.body` содержит извлечённый текст.
- [x] 3.3 Тест: plaintext предпочтительнее (оба поля заполнены) → `body` = plaintext.
- [x] 3.4 Тест: оба пусты → `body` пуст (без ошибки).

## 4. Stub-адаптер (симметрия, D4)

- [x] 4.1 В `src/infrastructure/mail/stub.py` применить ту же `extract_body_text(payload)`.
- [x] 4.2 Тест `tests/infrastructure/test_stub_mail.py`: HTML-only fallback отрабатывает аналогично Mailgun-пути.

## 5. Рефакторинг: единый хелпер выбора тела

- [x] 5.1 Общий fallback «выбрать тело из payload» вынесен в `extract_body_text` в `src/infrastructure/mail/html.py`; оба нормализатора используют его — порядок источников не дублируется.

## 6. Качество

- [x] 6.1 `uv run ruff check` чист (для `src/infrastructure/mail` и `tests/infrastructure`).
- [x] 6.2 `uv run ty check src` чист для production-кода (предсуществующий baseline-шум `unresolved-import: pytest/respx` в тестовых файлах — окруженческая проблема ty/venv, затрагивает весь репо и к этому change не относится).
- [x] 6.3 `uv run pytest` зелёный: 213 passed, 3 skipped; coverage 90.48% (gate 80% держится).
