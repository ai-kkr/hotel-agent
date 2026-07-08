## ADDED Requirements

### Requirement: Выбор LLM-провайдера по конфигурации

Система SHALL конструировать чат-модель (`BaseChatModel`) из конфигурации (`Settings.llm_model`) через единую
фабрику `build_model`, поддерживая как минимум провайдеров **openai** (default) и **zai** (Z.AI, OpenAI-compatible).

#### Scenario: Default-провайдер OpenAI
- **WHEN** `KKR_LLM_MODEL` не задан или равен `gpt-4o-mini` (без префикса)
- **THEN** система строит модель через `init_chat_model` с `model_provider="openai"`

#### Scenario: Явный OpenAI через префикс
- **WHEN** `KKR_LLM_MODEL="openai:gpt-4o-mini"`
- **THEN** система строит модель через `init_chat_model("openai:gpt-4o-mini", ...)`

#### Scenario: Провайдер Z.AI (glm-5.2)
- **WHEN** `KKR_LLM_MODEL="zai:glm-5.2"` и задан `KKR_ZAI_API_KEY`
- **THEN** система строит OpenAI-compatible модель с `model="glm-5.2"`,
  `api_base` равным `KKR_ZAI_API_BASE` (default `https://api.z.ai/api/paas/v4/`) и ключом из `KKR_ZAI_API_KEY`

#### Scenario: Неизвестный префикс провайдера
- **WHEN** `KKR_LLM_MODEL="<unknown>:foo"` с нераспознанным префиксом
- **THEN** система сообщает понятную ошибку конфигурации (не падает молча внутри вызова агента)

### Requirement: Валидация ключа Z.AI

Система SHALL fail-fast проверять наличие `KKR_ZAI_API_KEY` при выборе провайдера `zai`, сообщая понятную ошибку с
именем переменной окружения.

#### Scenario: Z.AI выбран без ключа
- **WHEN** `KKR_LLM_MODEL="zai:glm-5.2"` и `KKR_ZAI_API_KEY` пуст
- **THEN** `build_model` возбуждает исключение с указанием, что требуется `KKR_ZAI_API_KEY`

### Requirement: Параметризуемый endpoint Z.AI

Система SHALL позволять переопределять базовый URL Z.AI через `KKR_ZAI_API_BASE`, по умолчанию используя
`https://api.z.ai/api/paas/v4/`.

#### Scenario: Кастомный base URL
- **WHEN** `KKR_LLM_MODEL="zai:glm-5.2"` и `KKR_ZAI_API_BASE` задан
- **THEN** построенная модель использует именно этот `api_base`

### Requirement: Единая модель для всех агентов

Система SHALL предоставлять всем четырём агентам (extractor, discoverer, negotiator, reporter) одну и ту же
сконструированную модель — выбор провайдера прозрачен для агентов и не требует их правок.

#### Scenario: Смена провайдера не трогает агентов
- **WHEN** конфигурация переключается с OpenAI на Z.AI (`zai:glm-5.2`)
- **THEN** код агентов (`extractor`/`discoverer`/`negotiator`/`reporter`) и `build_agents` остаётся без изменений, а
  `build_model` возвращает совместимый `BaseChatModel`
