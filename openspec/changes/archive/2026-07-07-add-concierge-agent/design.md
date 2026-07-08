# Design: Hotel Concierge Agent (kkr-hotel-assist)

> Черновик архитектуры. Зафиксирован в explore-режиме как фиксация мышления, не реализация.
> Артефакт `proposal.md` ещё не создан — дополнить мотивацией/скоупом следующим шагом.

## Context

**kkr-hotel-assist** — email-агент-консьерж. После бронирования отеля клиент пересылает
(forward) письмо-подтверждение на индивидуальный почтовый ящик. Агент разбирает подтверждение,
определяет отель и его контактный email, и ведёт переписку с отелем от лица клиента, решая
на старте две задачи: **ранний заезд** (early check-in) и **условия апгрейда номера**, плюс
свободные **пожелания** клиента. Итоговый отчёт направляется клиенту; после отчёта клиент может
дать новый ввод — агент удерживает контекст и снова может сходить к отелю.

**Канал на v1** — email в обе стороны (с клиентом и с отелем). При этом **всё channel-facing
за адаптерами**: клиентский канал проектируется сразу омиканально (email → Telegram / WhatsApp /
нативное приложение с агентом), отельный — mail (Mailgun) с возможностью замены.

**Стек** (из `openspec/project.md`): Python, FastAPI, PostgreSQL + SQLAlchemy, `uv`,
Clean Architecture (domain / infrastructure / presentation). Дополнительно оговорено:
- **Temporal** — durable long-running execution (оркестрация).
- **LangGraph** — LLM-агент; извлечение данных из писем, формирование текста и интеллектуальная
  многотурновая переписка с отелем — на агенте; есть тул `web_search`.
- **Почтовый сервис** — внешний, на старте **Mailgun**. Inbound — webhook, outbound — API.
  Переключаемо конфигом через адаптеры (гибкость под самописный сервис).

Проект greenfield — исходного кода нет, только конституция.

## Goals / Non-Goals

**Goals:**
- Принять форвард подтверждения + пожелания → извлечь данные → инициировать переговоры с отелем по дефолтным темам (check-in, upgrade) и пожеланиям.
- Durable-исполнение: переписка живёт днями, корректно переживает ожидание ответа, таймауты, фоллоу-апы, ретраи, рестарты.
- Интеллектуальная многотурновая переписка с отелем через LLM-агента; переписка ведётся на **языке отеля**.
- Контекст агента полностью контролируется **checkpoint saver** LangGraph, на уровне **брони** (per-booking thread).
- Гибкость каналов: и отельный, и клиентский канал — за адаптерами; клиентский сразу готов к омиканальности (v1 = email).
- Удержание контекста после отчёта: повторный ввод от клиента → новый тур агента → повторный заход к отелю.

**Non-Goals (на старте):**
- Платежи и cost-binding решения агентом: **стоимость апгрейда — это просто информация для клиента**, агент не авторизует оплату и не требует approval-gate по деньгам.
- Реализация не-email клиентских каналов (Telegram/WhatsApp/native) — только архитектурная готовность; сами адаптеры позже.
- Интеграции с API booking-платформ (Booking.com и т.п.) — отдельно, позже.
- Полная автономия на необратимых действиях (отмена брони и т.п.).

## Architecture Overview

Единица оркестрации и единица контекста — **бронь** (booking). Один `BookingWorkflow` владеет
одним разговором с отелем и одним LangGraph-thread; темы (check-in, upgrade, пожелания) трекаются
внутри как доменные сущности, а не как отдельные воркфлоу.

```
   ┌────────────── channel adapters (всё channel-facing — за портами) ──────────────┐
   │  HOTEL side:  Mail (Mailgun)         │  CLIENT side:  Mail (Mailgun) on v1   │
   │               catch-all route, webhook│               → Telegram/WhatsApp/    │
   │               + send API              │                 native app later      │
   └───────────────┬───────────────────────┴────────────────────┬──────────────────┘
                   ▼ inbound normalizers                         ▲ outbound gateways
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │ FastAPI (presentation)                                                       │
   │   POST /webhooks/{provider}/inbound   POST /webhooks/{provider}/status       │
   │   POST /api/client-message  (и будущие канальные вебхуки)                    │
   └───────────────────────────────┬──────────────────────────────────────────────┘
                                   ▼  нормализация в доменные события
                          ┌────────────────────┐
                          │ Inbound dispatcher │  dispatch по local-part + sender:
                          └─────────┬──────────┘    c.<token>  → intake (new booking)
                                    │               b.<booking> → BookingWorkflow signal
                                    │               (sender = hotel | client)
                                    ▼
   ┌─ Temporal (durable spine) ──────────────────────────────────────────────────┐
    BookingWorkflow   (workflow_id = booking_id)   ← единственный writer thread'а
      ① extract(forward, wishes) ▶ [LangGraph thread init] → booking + topics + hotel info
      ② discover_contact (if missing) ▶ [LangGraph + web_search/fetch_url]
            → hotel contact + language
      ③ conversation loop:
           agent_turn(thread, goal) ▶ intent         ← checkpoint saver, per-booking
              ▼ [LangGraph negotiation-агент + tools]
           apply intent:
              send_email (batched, reply-to b.<booking>@, idempotent key booking:step)
            | resolved-partial → follow-up
           await signal(on_hotel_reply) | timer(timeout)
              └─ timeout → agent_turn(follow-up); reply → agent_turn(parse, update topics)
           ... пока все открытые темы не закрыты / can't-progress
      ④ build_report ▶ [LangGraph] ▶ ClientNotifier.notify
      ⑤ await signal(client_followup)   ← долгоживущий, омиканальный источник
              └─ новый топик/данные → обратно в ③ (возможно второе письмо отелю)
   └─────────────────────────────────────────────────────────────────────────────┘
```

## Decisions

### D1. Бронь — единица оркестрации и контекста; Temporal spine + LangGraph turn-brain
Один `BookingWorkflow` (один `workflow_id = booking_id`) владеет всем разговором с отелем.
Ожидание ответа (часы/дни) — `signal | timer` Temporal; внутри одного хода воркфлоу в активити
зовёт LangGraph-агента, тот решает следующий ход и возвращает intent. Темы (check-in, upgrade,
пожелания) — доменные сущности внутри брони, трекаются агентом и в Postgres, **не** отдельными
воркфлоу. Альтернатива «N RequestWorkflow, каждый со своим письмом» — отвергнута: конфликтует
с пакетной отправкой (D7) и создаёт гонку записей в общий thread.

### D2. LLM/агент-вызовы — ТОЛЬКО внутри активити, никогда в коде воркфлоу
Temporal реплеит воркфлоу детерминированно; LLM в workflow-коде ломает replay. Все инвокации
LangGraph — внутри активити; результат пишется в history и переиспользуется при replay.
**Non-negotiable.**

### D3. Агент производит intent; воркфлоу исполняет side-effects
У агента **нет** тула `send_email` (и иных side-effect тулов). Агент возвращает структурированные
интенты (`send_email(body)`, `search_done`, `resolved(summary)`, `need_more_info`), воркфлоу
применяет их через активити. Идемпотентность/аудит/durable-граница остаются в Temporal; агент
replay-safe и тестируем. Tools у агента — только чтение: `web_search`, `fetch_url` (сайт отеля),
`recall_booking` / `read_history`, опц. `lookup_hotel_directory`.

### D4. Контекст LangGraph — на checkpoint saver, per-booking (`thread_id = booking_id`)
Контекст агента (история переговоров, накопленное понимание, wishes, scratchpad, язык отеля)
хранится и версонируется **checkpoint saver** LangGraph (PostgresSaver). `thread_id = booking_id`.
Каждый `agent_turn` резюмит граф из чекпоинта, инжектит событие, прогоняет внутренний ReAct-цикл,
чекпоинтится, возвращает intent. Ручной рефид истории не нужен.

**Почему per-booking, не per-request (решённый Open Question):** единая память разговоров +
требование пакетных писем (D7) естественны на уровне брони. И главное — **один воркфлоу = один
thread = один writer**: потенциальная гонка записей в LangGraph-thread, которая была бы при
per-request, исчезает (нет конкурентных активити, пишущих один thread).

### D5. Три хранилища, разделённые по ответственности
- **Postgres** — domain source of truth: клиенты, брони, темы(requests)/их статусы, сообщения, wishes, итоги, отчёты. То, что показываем/агрегируем.
- **Temporal** — execution state: где бронь в lifecycle, открытые таймеры/сигналы, история активити.
- **LangGraph checkpointer** — agent memory: контекст рассуждения.

Активити обновляют Postgres на ключевых переходах (`EMAIL_SENT`, `TOPIC_ANSWERED`, `RESOLVED`,
`REPORT_SENT`). Дублирование осмысленное.

### D6. ID = local-part = `workflow_id` = `thread_id` = `booking_id`
Один сквозной идентификатор брони связывает маршрутизацию, оркестрацию и память. Catch-all
`*@kkr-hotel.com`, диспатч по local-part + отправителю:
- `c.<client-token>@` — первичный intake: клиент форвардит подтверждение. token неугадываемый + SPF/DKIM (отправитель = зарегистрированный email клиента). token→client→new/existing booking.
- `b.<booking_id>@` — **booking-scoped** адрес разговора; ставится как `Reply-To` во **всех** исходящих (и отелю, и клиенту). Любой inbound на него → сигнал `BookingWorkflow(booking_id)`; диспетчер различает отель/клиента по `From`.

`workflow_id` Temporal = `booking_id`; `thread_id` LangGraph = `booking_id`. Маршрутизация «бесплатная».

### D7. Пакетная отправка: одно письмо на бронь покрывает все открытые темы
Стараемся уложить все вопросы отелю (check-in, upgrade, пожелания) в **одно письмо**. Второе
письмо тому же отелю — только если клиент дослал что-то сверху или потребовался фоллоу-ап по
частично-ответленной теме. Ответ отеля приходит на `b.<booking_id>@` → агент на per-booking thread
разбирает, какие темы закрыты, какие требуют уточнения. Альтернатива «отдельный тред на каждый
вопрос» отвергнута: раздражает отель множественностью и конфликтует с per-booking контекстом.

### D8. Омиканально-готовые клиентские каналы (port-пары в обе стороны)
Канальный слой — единообразно через пары адаптеров:
- outbound: `OutboundGateway.send(...)` — `MailOutboundGateway` (Mailgun) для отеля и для клиента на v1; будущие `TelegramGateway`, `WhatsAppGateway`, `NativeAppGateway`.
- inbound: `InboundNormalizer.parse(req) → event` — `MailWebhookNormalizer` (Mailgun) на v1; будущие нормализаторы под вебхуки мессенджеров / in-app.

Клиентский ввод унифицирован в доменное событие `ClientMessage` (email-реплай, Telegram, WhatsApp,
in-app, `POST /api/client-message` — любой источник). Отельный ввод — `HotelReply`. Оба способны
возобновить `BookingWorkflow`. v1 реализован только email-адаптер; порты и диспетчер существуют
сразу, поэтому апгрейд до омиканальности — добавление адаптеров, не переделка ядра.

### D9. Доставка отчёта/нотификаций — за адаптером
`ClientNotifier.notify(client, report)` — email на v1, за портом, чтобы позже направлять в
Telegram/WhatsApp/push/in-app. Симметрично D8.

### D10. Язык переписки — язык отеля; fallback на английский
Агент определяет язык отеля из контекста: локаль подтверждения, сайт отеля (`fetch_url`),
`web_search`; ведёт переписку на этом языке; если определить не удалось — английский. Определение
языка — часть построения контекста (в extract/discover), сохраняется в per-booking thread.

### D11. Долгоживущий контекст брони и повторный заход к отелю
После `build_report` воркфлоу **не закрывается**, а ждёт `client_followup`. Повторный ввод
(любой канал, D8) → `agent_turn` резюмит per-booking thread с обновлённым контекстом → при
необходимости повторный заход к отелю (возможно второе письмо, D7). «Стоимость апгрейда» и прочее —
просто поля в контексте/отчёте; агент по деньгам решений не принимает (Non-Goal).

### D12. Идемпотентная отправка
`send_email`-активити с детерминированным idempotency-key (`booking_id:step`, напр. `b42:initial`,
`b42:followup1`). Защита от классической Temporal-ловушки (ретрай активити на границе отправки →
два письма). Mailgun поддерживает replay-защиту.

## Inbound routing & event model

```
   email (mailgun webhook)
     c.<token>@    → ConfirmForward        → start BookingWorkflow
     b.<booking>@  → HotelReply | ClientMessage (по From) → signal BookingWorkflow
   api            → POST /api/client-message → ClientMessage              → signal
   (будущее)      → telegram/whatsapp/in-app вебхуки → ClientMessage       → signal
                                   │
                                   ▼  единые доменные события
                          ┌────────────────────┐
                          │ Inbound dispatcher │
                          └────────────────────┘
```

Любой вход трактуется как доменное событие, стартующее или сигналящее `BookingWorkflow`. Добавление
нового канала = новый адаптер + нормализатор в событие, без правок ядра/воркфлоу.

## Booking/conversation lifecycle

```
INTAKE → EXTRACTED → CONTACT_READY → IN_CONVERSATION ⇄ AWAITING_REPLY → TOPICS_RESOLVED
                          │                │               │
                          │                │               ├─▶ PARTIAL → FOLLOWUP → AWAITING_REPLY
                          │                │               └─▶ NO_REPLY(timeout) → FOLLOWUP
                          │                └─▶ AMBIGUOUS_REPLY → IN_CONVERSATION (уточнение)
                          └─▶ CONTACT_NOT_FOUND → CAN'T_PROGRESS (human/notify client)
   TOPICS_RESOLVED → REPORT_SENT → AWAITING_CLIENT_FOLLOWUP → (реактивация в IN_CONVERSATION)
```

Состояние отдельных тем (check-in / upgrade / wish) трекается внутри как под-статусы в Postgres,
обновляется агентом каждый ход; отчёт строится из них. Бронь остаётся «открытой» после отчёта.

## Wishes (пожелания)

Самый email-native способ — клиент пишет пожелания в сопровождении форварда (вне forwarded-блока).
Экстракшн-агент (D4/extract) и так читает входящее — он же разнимет «обложку клиента» от
бойлерплейта платформы. Эффекты:
- **новые темы** — помимо дефолтных (check-in, upgrade) появляются «поздний выезд», «высокий этаж»
  и т.п.; они войдут в то же пакетное письмо (D7), если пришли до отправки, либо во второе — если после.
- **контекст переговоров** — «апгрейд только если вид на море». На v1 — free-text контекст в
  per-booking thread; структурировать позже.

## Risks / Trade-offs

- **Доставание email отеля** → митигировано `web_search`+`fetch_url`, **не решено** на 100% (иногда контакта нет в природе). Фолбэк: `CAN'T_PROGRESS` → уведомление клиента / передача человеку.
- **Отель отказывается обсуждать бронь с не-гостем** (защита данных) → world-блокер, архитектурой не лечится. Митигация: цитируем booking-ref + имя гостя; graceful failure.
- **LLM-недетерминизм в активити** → запись результата в history + intent-модель (D3); tools только read-only → ретраи `agent_turn` безопасны.
- **Гонка записей в LangGraph-thread** → **устранена** выбором per-booking (D4): один воркфлоу = один writer.
- **Дубликат отправки при ретрае** → idempotency-keys (D12).
- **«Агент вытащил мусор» из подтверждения / неверный язык** → structured output + валидация + low-confidence → уточняющий запрос клиенту; язык — fallback на английский (D10).
- **Email deliverability** (новый домен пишет отелям) → SPF/DKIM/DMARC, прогрев домена, мониторинг bounce-rate.
- **PII в пересылаемых подтверждениях** → retention-политика, at-rest шифрование; уточнить требования (Open Question).

## Migration Plan

N/A — greenfield. Развёртывание: Temporal server + Postgres + LangGraph PostgresSaver (отдельная
схема той же Postgres) + Mailgun-аккаунт с catch-all route и подписанным вебхуком. Rollback = снять
воркера и вебхук; данные клиентов в Postgres не теряются.

## Open Questions

1. **Schema structured-output** для экстракции подтверждения: обязательные поля (hotel name/address, dates, booking-ref, guest names, room type, *hotel contact если есть*), правила валидации, порог confidence.
2. **Триггер отчёта**: кто/что считает темы «достаточно закрытыми» для `build_report` — агент решает сам, или правило «все дефолтные темы resolved + N дней без новых вводов»?
3. **Несколько активных броней у одного клиента**: как `b.<booking_id>` соотносится с `c.<token>` — один token на клиента со списком бронь, или токен пересоздаётся? Влияет на intake-диспетчер.
4. **Онбординг клиента / выдача `c.<token>`** — за пределами этого дизайна, но зависимость.
5. **Retention/PII** для пересылаемых подтверждений — требования по хранению и удалению.
