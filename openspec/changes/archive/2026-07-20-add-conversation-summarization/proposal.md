## Why

Длинные переписки (много ходов с гостем, длинные ответы отеля, несколько раундов поиска)
раздувают `state["messages"]` и упираются в контекстное окно модели. Существующая
компактизация (`cleanup`) режет только одноразовый вывод `search_internet`/`extract_web_page`
на конце хода — это не помогает, когда растёт сама беседа. Нужен запасной клапан: когда вход
модели превышает мягкий порог, сжать старую часть переписки в бегущее саммари, чтобы агент
продолжил без шва и не упёрся в лимит.

## What Changes

- **Новая нода `summarize` + conditional-проверка `summarize_check`** перед `model`. Проверка
  читает `last_prompt_tokens` (см. ниже) и решает — запускать саммаризацию или сразу в `model`.
  Граф: `START/tools → summarize_check → summarize → model` (или `→ model`).
- **Сигнал о размере контекста — из ответа самой модели**, без локального токенайзера.
  `model_node` после `model.ainvoke` читает `result.usage_metadata["input_tokens"]` (реальный
  размер `[SYSTEM_MAIN, *messages]`) и кладёт в новое поле стейта `last_prompt_tokens: int`.
- **Бегущее саммари в отдельном поле стейта** `conversation_summary: str | None`, а не как
  сообщение в истории. `model_node` препендит его как `SystemMessage` при invoke — саммари
  всегда первое, аккумулируется при повторных сжатиях, промпт-инструкция не пачкает историю.
- **Сжатие через `RemoveMessage`** (штатный `add_messages`-редьюсер удаляет по id): нода
  удаляет старый префикс, оставляет recency-окно (последний ход гостя + его работа). Граница
  среза **обязана** держать пару `AIMessage(tool_calls) ↔ ToolMessage(s)` целой.
- **Отдельный промпт** `system_summarize.md` — одноразовый скрытый LLM-вызов (не ход агента):
  фокус на текущей цели и следующем шаге, обязательно сохранить вехи/решения/данные (бронь,
  email отеля, отправленные письма и `message_id`, ответы отеля, плановые задачи, пожелания,
  открытые вопросы).
- **Уведомление гостя** перед саммаризацией (`⏳ Переписка стала длинной — подвожу итог…`),
  т.к. это лишний LLM-вызов на 5–30 сек.
- **Новые настройки**: `summarize_token_threshold` (мягкий порог входа, дефолт 100000),
  `summarize_keep_last_messages` (размер recency-окна, дефолт 6). Оба — в `config.py` + `config.yaml`.

## Capabilities

### New Capabilities
- `conversation-summarization`: авто-сжатие длинной переписки в бегущее саммари при превышении
  мягкого порога контекста — триггер, механика сжатия (recency-окно + `RemoveMessage`), что
  сохраняет промпт саммаризации, уведомление гостя.

### Modified Capabilities
<!-- Никто. `context-compaction` (per-turn стаббинг вывода поиска) остаётся без изменений —
     это ортогональный механизм. -->

## Impact

**Код.** `src/agent/agent.py` (новая нода `summarize_node`, conditional `summarize_check`,
edge-перестановка `tools → summarize_check` вместо `tools → model`, препенд саммари в
`model_node`, запись `last_prompt_tokens`); `src/agent/state.py` (новые поля
`conversation_summary`, `last_prompt_tokens`); `src/agent/prompts/system_summarize.md`;
`src/config.py` + `config.yaml` (две настройки). Возможно — выделение логики в
`src/agent/summarization.py` (по аналогии с `compaction.py`).

**Сериализуемость и Temporal-граница (high-risk зоны).** Новые поля стейта — чистый JSON
(`str | None`, `int`), проходят round-trip через `StateType` (JSONB) и
`message_aware_data_converter` без schema-изменений. Новая нода — это ещё одна Temporal
activity (свой `start_to_close_timeout >= llm_timeout_seconds`, retry-policy, Langfuse), как
`model`/`cleanup`. `EmailContext` не трогается — тяжёлые зависимости (модель) нода достаёт
через `get_context()`, как всегда. **Email threading не затрагивается.**

**Новый инструмент в `src/agent/tools/`?** Нет — это граф-нода, не тул; агент её не вызывает.

**Деплой.** Новые env-настройки (`KKR_SUMMARIZE_TOKEN_THRESHOLD`,
`KKR_SUMMARIZE_KEEP_LAST_MESSAGES`) с дефолтами — работают и без явной установки. **Миграции
Alembic не требуется** (новые поля лежат в существующем JSONB-столбце `states.state`).
Нужен `railway up --service app --detach -m "…"` на `main` + поллинг до SUCCESS. Бот-контур
prod изолирован от dev, останавливать ничего не надо.

## Non-goals

- **Защита первого хода** от гигантского пересланного `.eml` брони: на первом model-вызове
  прошлого `usage` ещё нет, порог не сработает. Принимается как известное ограничение (латать
  char-эвристикой вне этого изменения).
- **Жёсткая защита от overflow** контекстного окна — это мягкий порог для удержания запаса, а
  не краш-барьер.
- Изменение существующей компактизации (`cleanup`) — она остаётся как есть.
- Ручное управление саммари со стороны гостя/агента (тул «засаммаризуй сейчас»).
