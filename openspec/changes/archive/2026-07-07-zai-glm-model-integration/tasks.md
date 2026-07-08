## 1. Конфигурация провайдера

- [x] 1.1 В `src/infrastructure/config.py` (`Settings`) добавить поля: `zai_api_key: str = ""` и
      `zai_api_base: str = "https://api.z.ai/api/paas/v4/"` (prefix `KKR_`).
- [x] 1.2 Оставить `llm_model` default `gpt-4o-mini` без изменений.

## 2. Фабрика модели

- [x] 2.1 В `src/infrastructure/agents/models.py` обновить `build_model`:
  - если `llm_model` начинается с `zai:` → маппить в `init_chat_model("openai:" + name, base_url=..., api_key=...)`
    с `settings.zai_api_base` / `settings.zai_api_key`, `temperature=0`;
  - оставить существующие ветки (префикс `openai:` / bare name → `openai`);
  - для неизвестного префикса возбуждать `ValueError` с понятным сообщением.
- [x] 2.2 Fail-fast: при `zai:` и пустом `settings.zai_api_key` возбуждать `ValueError` с указанием
      `KKR_ZAI_API_KEY`.
- [x] 2.3 Обновить docstring `build_model` (упомянуть провайдеры openai/zai и формат `"<provider>:<model>"`).

## 3. Тесты

- [x] 3.1 Создать `tests/agents/test_models.py` (или `tests/infrastructure/`) с моком `init_chat_model` /
      `ChatOpenAI`.
- [x] 3.2 Тест: bare `gpt-4o-mini` → `init_chat_model(..., model_provider="openai")`.
- [x] 3.3 Тест: `openai:gpt-4o-mini` → `init_chat_model("openai:gpt-4o-mini", ...)`.
- [x] 3.4 Тест: `zai:glm-5.2` с ключом → модель строится с `base_url=settings.zai_api_base` и
      `api_key=settings.zai_api_key`.
- [x] 3.5 Тест: `zai:glm-5.2` без ключа → `ValueError` упоминает `KKR_ZAI_API_KEY`.
- [x] 3.6 Тест: кастомный `KKR_ZAI_API_BASE` пробрасывается в построенную модель.
- [x] 3.7 Тест: неизвестный префикс `<unknown>:foo` → понятная ошибка.

## 4. Документация

- [x] 4.1 В `docs/ops.md` (таблица переменных) добавить `KKR_LLM_MODEL` (формат `zai:glm-5.2`), `KKR_ZAI_API_KEY`,
      `KKR_ZAI_API_BASE`; упомянуть, что для локального запуска с glm-5.2 используется `KKR_LLM_MODEL=zai:glm-5.2`.
- [x] 4.2 Обновить `.env.example` (из соседнего change `local-agent-run-harness`, либо создать при отсутствии):
      добавить `KKR_LLM_MODEL`, `KKR_ZAI_API_KEY=` (плейсхолдер), `KKR_ZAI_API_BASE`.

## 5. Definition of Done

- [x] 5.1 `uv run ruff check` — без предупреждений _(на изменённых файлах: чисто;
      предсуществующий `main_experiment.py:32` unused `mail_gateway` вне scope этого change)._
- [x] 5.2 `uv run ty check` — чисто _(на изменённых файлах: чисто; ~95 предсуществующих
      диагностики по другим модулям/сторонним стабам вне scope)._
- [x] 5.3 `uv run pytest` — зелёно, покрытие ≥ 80 % _(166 passed, 1 skipped, 86.42 %)_.
- [x] 5.4 Ручная проверка: с реальным `KKR_ZAI_API_KEY` (Coding Plan, `open.bigmodel.cn`) `ConfirmationExtractorAgent`
      корректно извлёк бронирование из образца на `glm-5.2` (confidence 0.99, все поля).
      `glm-5.2`.
