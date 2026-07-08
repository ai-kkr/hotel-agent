## Why

Едиственный поддерживаемый провайдер LLM сейчас — OpenAI: `infrastructure/agents/models.build_model` через
`init_chat_model` всегда выводит `model_provider="openai"`, а `Settings.llm_model` по умолчанию `gpt-4o-mini`. Чтобы
запустить агентов на модели **Z.AI `glm-5.2`** (OpenAI-compatible API по `https://api.z.ai/api/paas/v4/`), нужен
способ выбрать этого провайдера и прокинуть его `api_key`/`api_base` — сегодня это невозможно без правок кода.
Добавление второго провайдера заодно проверяет, что конструкция модели действительно провайдеро-агностична.

## What Changes

- Добавлен провайдер **Z.AI** (модель `glm-5.2`) как новое значение выбора LLM-провайдера: `build_model` строит
  `ChatOpenAI` с `openai_api_base="https://api.z.ai/api/paas/v4/"` и ключом из конфигурации.
- `Settings` расширен: способ указать провайдера/модель (`zai:glm-5.2` или отдельные поля `zai_api_key` /
  `zai_api_base`, default base — `https://api.z.ai/api/paas/v4/`).
- Поведение по умолчанию (OpenAI / `gpt-4o-mini`) не меняется; z.ai активируется конфигурацией.
- Локальный запуск (см. соседний change `local-agent-run-harness`) может использовать `glm-5.2` через `.env`.

## Capabilities

### New Capabilities

- `chat-model-providers`: выбор и конструкция LLM-провайдера (OpenAI / Z.AI `glm-5.2`) по конфигурации; единая
  фабрика `build_model`, отдающая `BaseChatModel`, который принимают все агенты.

### Modified Capabilities

_(нет — отдельной спеки для LLM/агентов до сих пор не было; она заводится в этом change.)_

## Impact

- **Код**: `src/infrastructure/config.py` (новые поля `llm_provider`/`zai_api_key`/`zai_api_base` или парсинг
  `zai:`-префикса в `llm_model`); `src/infrastructure/agents/models.py` (`build_model` — ветка Z.AI через
  `ChatOpenAI` с кастомным `base_url`).
- **Зависимости**: новых пакетов не нужно — `langchain-openai` (содержит `ChatOpenAI`) уже в `pyproject.toml`.
- **Конфигурация**: новые переменные окружения (`KKR_LLM_MODEL=zai:glm-5.2`, `KKR_ZAI_API_KEY`,
  `KKR_ZAI_API_BASE`); `.env.example` (из соседнего change) — обновить.
- **Документация**: `docs/ops.md` (таблица переменных) — добавить z.ai.
- **Тесты**: unit-тесты на `build_model` для обоих провайдеров (мок `init_chat_model`/`ChatOpenAI`); покрытие ≥ 80 %.
- **Совместимость**: не breaking — default `openai`/`gpt-4o-mini` сохранён.
