# Project Constitution: kkr-hotel-assist

## 1. Executive Summary & Purpose
* **Core Goal**: Реализация агента-консьержа, помогающего с отелем после его бронирования (разговор с отелем от лица пользователя, запрос улучшения категории номера, запрос раннего заезда, запрос дополнительных опций по питанию и тд)
* **Target Audience**: клиенты, бронирующие отели

## 2. Technology Stack & Environment
* **Language**: Python
* **Backend**: FastAPI
* **Database**: PostgreSQL + sqlalchemy
* **Runtime Restrictions**: uv
* **Durable Orchestration**: Temporal (обязательная зависимость — долговременное исполнение, long-running переговоры с отелем)
* **Agent Framework**: LangGraph (обязательная зависимость — всё извлечение данных из писем, формирование текста и переговоры ведутся через LLM-агента)

## 3. Architecture & Code Organization
* **Pattern**: Clean Architecture (Разделение на Layers: entities, use-cases, controllers, gateways).
* **Directory Structure**:
  * `/src/domain` — Бизнес-логика, сущности и интерфейсы.
  * `/src/infrastructure` — Базы данных, внешние API, конфигурация.
  * `/src/presentation` — Эндпоинты, контроллеры, роутинг.

## 4. Execution Philosophy & Global Rules (Для ИИ)
* **Rule 1**: Сначала всегда пиши тесты (TDD), если это возможно, либо покрывай новый код модульными тестами минимум на 80%.
* **Rule 2**: Никогда не удаляй существующую обработку ошибок и логгирование.
* **Rule 3**: Используй аннотации типов во всём коде; `ty check` должен быть чистым.
* **Rule 4**: Пиши код декларативно, избегай глубокой вложенности условий (используй Early Returns).
* **Rule 5**: Если фича требует изменения БД, всегда создавай файл миграции, не меняй схему «вживую».
* **Rule 6**: Управляй зависимостями только через `uv` и `pyproject.toml`; не добавляй пакеты иными способами.
* **Rule 7**: Соблюдай направление зависимостей Clean Architecture: внешние слои (`presentation`, `infrastructure`) могут зависеть от внутренних, но `domain` не зависит ни от кого (не импортирует `infrastructure`/`presentation`).

## 5. Definition of Done (Критерии готовности задач)
Перед тем как отметить задачу выполненной (`[x]`) в файле `tasks.md`, ИИ-ассистент обязан:
1. Запустить линтер командой `ruff check` и исправить все предупреждения.
2. Проверить типы и синтаксис `ty check`.
3. Успешно выполнить весь пул тестов `uv run pytest`.


