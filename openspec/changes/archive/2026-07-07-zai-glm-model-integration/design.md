## Context

Все четыре агента (extractor/discoverer/negotiator/reporter) принимают `BaseChatModel` и собираются в
`build_agents(settings, model=...)`. Саму модель строит `infrastructure/agents/models.build_model(settings)`:

```python
model = settings.llm_model               # default "gpt-4o-mini"
if ":" in model:
    return init_chat_model(model, temperature=0)
return init_chat_model(model, model_provider="openai", temperature=0)
```

`init_chat_model` из `langchain.chat_models` по строке `"<provider>:<model>"` выбирает адаптер. Z.AI — это
OpenAI-compatible API: достаточно собрать `ChatOpenAI(model="glm-5.2", openai_api_base=<z.ai>, openai_api_key=...)`.
`init_chat_model("openai:glm-5.2", base_url=..., api_key=...)` прокидывает kwargs в `ChatOpenAI`, поэтому отдельный
класс не нужен — нужен только способ сказать фабрике «используй z.ai base_url и z.ai ключ».

Ограничения (`openspec/project.md`): зависимости только через `uv`/`pyproject.toml` (пакет уже есть); Clean
Architecture (конструкция модели — infrastructure); типы/`ty` чистый; TDD/покрытие ≥ 80 %.

## Goals / Non-Goals

**Goals:**

- Запускать всех агентов на **Z.AI `glm-5.2`** выбором конфигурации, без правок агентов.
- Сохранить OpenAI как default без изменений поведения.
- Единая точку конструкции модели (`build_model`), расширяяемая под будущих OpenAI-compatible провайдеров.

**Non-Goals:**

- Поддержка не-OpenAI-compatible провайдеров (Anthropic native и т.п.) — вне scope; нужен был именно z.ai.
- Сравнение качества/тюнинг `temperature`/параметров модели — фиксируем `temperature` как сейчас (0), кроме случаев,
  где агенты уже задают своё (поведение не меняем).
- Роутинг разных моделей разным агентам (extractor на одной, negotiator на другой) — одна модель на всех, как сейчас.

## Decisions

### D1. Провайдер задаётся префиксом в `llm_model` (`zai:glm-5.2`), ключи — отдельными полями

**Решение:** переиспользовать существующий `init_chat_model("<provider>:<model>")` контракт. В `Settings` добавляем:

- `zai_api_key: str = ""`
- `zai_api_base: str = "https://api.z.ai/api/paas/v4/"`

В `build_model`: если `llm_model` начинается с `zai:`, строим
`init_chat_model("openai:" + model_after_prefix, base_url=settings.zai_api_base, api_key=settings.zai_api_key,
temperature=0)` (Z.AI совместим с OpenAI); иначе текущее поведение.

**Альтернатива A:** отдельное поле `llm_provider: Literal["openai","zai"]`. Отклонено — дублирует уже
существующий префиксный механизм `"<provider>:<model>"`, который парсится в `build_model`; два источника истины
провоцируют рассинхрон (`llm_provider="zai"` + `llm_model="openai:gpt-4o-mini"`).

**Альтернатива B:** разрешить произвольный `openai:glm-5.2` + общие `openai_api_base`/`openai_api_key`. Отклонено —
неявно, и путает с настоящим OpenAI; явный префикс `zai:` самодокументирует провайдера и позволяет валидировать
наличие `zai_api_key`.

### D2. Валидация ключа на старте

**Решение:** при выборе `zai:` фабрика падает с понятной ошибкой, если `zai_api_key` пуст (`ValueError` с указанием
`KKR_ZAI_API_KEY`). Это ловит misconfig рано, а не внутри первого вызова агента в Temporal-активности.

### D3. Z.AI ключ из окружения, не в коде

**Решение:** ключ — только `KKR_ZAI_API_KEY` (через `pydantic-settings`, как остальные креды). `.env` не коммитится
(включая будущий `.env.example`, который содержит плейсхолдер).

### D4. Базовый default захардкожен в `Settings`

**Решение:** `zai_api_base` default — **Coding Plan** OpenAI-эндпоинт
`https://open.bigmodel.cn/api/coding/paas/v4` (биллинг по подписке GLM Coding Plan, не PaaS-баланс),
переопределяется через `KKR_ZAI_API_BASE`. Для международного pay-as-you-go PaaS использовать
`https://api.z.ai/api/paas/v4/`. Первоначальный ТЗ-эндпоинт `api.z.ai/api/paas/v4` оказался путём с отдельным
PaaS-балансом — исправлено на coding-эндпоинт по итогам проверки.

### D5. Structured output через function-calling

**Решение:** в агентах с `model.with_structured_output(Schema)` явно указывать `method="function_calling"`.
OpenAI-compatible модели (GLM на coding-эндпоинте) при JSON-schema/response_format пути оборачивают ответ в
markdown-fences (```` ```json ````), ломая строгий парсинг OpenAI SDK. Function-calling возвращает аргументы как
чистый JSON внутри tool-call — надёжно. Применено в `ConfirmationExtractorAgent`; для
`create_agent(..., response_format=...)` (discoverer/negotiator) — отдельная проверка при необходимости.

## Risks / Trade-offs

- **[Z.AI API-поверхность отличается от OpenAI в edge-cases]** → tool-calling/structured-output могут вести себя
  иначе; Mitigation: агенты уже используют `create_agent` + `with_structured_output`/`bind_tools` (стандартный
  LangChain-контракт, поддерживаемый OpenAI-compatible); при расхождениях — отдельный follow-up, не блокируя базовую
  интеграцию.
- **[Префикс `zai:` — нестандартный для `init_chat_model`]** → мы сами маппим `zai:` → `openai:` + base_url; если
  передать `zai:glm-5.2` напрямую в `init_chat_model`, он упадёт — поэтому маппинг обязан быть в `build_model`.
  Mitigation: тест на маппинг + понятная ошибка для неизвестного префикса.
- **[Пустой ключ ловится поздно]** → решено D2 (fail-fast).
- **[Расходы/рейт-лимиты z.ai]** → вне scope кода; в docs упомянуть, что ключ платный.

## Migration Plan

1. Добавить поля в `Settings` (`zai_api_key`, `zai_api_base`) и ветку `zai:` в `build_model`.
2. Тесты на оба провайдера + валидацию ключа.
3. Обновить `.env.example` (соседний change) и таблицу в `docs/ops.md`.
4. Откат — default `openai` работает без изменений.

## Open Questions

- Достаточно ли `temperature=0` (текущий default) для `glm-5.2`, или закладывать настраиваемую температуру (в ТЗ
  упоминается `0.6`)? Текущее решение: оставить `0` для детерминизма агентов (как сейчас); если потребуется —
  добавим `KKR_LLM_TEMPERATURE` отдельным изменением.
- Нужен ли `llm_provider`-agnostic реестр провайдеров, или префиксного маппинга в `build_model` хватает на
  ближайшее время? Текущее решение: маппинга достаточно до 3–4 провайдеров.
