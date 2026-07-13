import asyncio
from pprint import pprint

from langchain_core.utils.uuid import uuid7
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from src_v2.agent.nodes.email_extractor import get_email_graph
from src_v2.agent.types import AgentContext
from tavily import TavilyClient

from infrastructure.config import get_settings

settings = get_settings()
# model = build_model(settings, model_override="glm-4.7")
model = ChatOpenAI(
    model_name="glm-5.2",
    openai_api_base="https://open.bigmodel.cn/api/coding/paas/v4",
    reasoning_effort="low",
)


email_text = """
Мне нужен номер по-ближе к морю. Нужен букет цветов в номер.


Продажа произведена
Dobedan Beach Resort Comfort
Бронирование 1 из 1
Оригинал
General Informations / Общая информация
Booker Name / Имя бронирующего  andrey victorov
Phone No / Телефон / Fax No  79267519272
Status / Статус  Продажа произведена
E- Mail / Эл. Почта  andvikt@gmail.com
Ваучер  WB6335
Price Date / Дата запроса  27.04.2025 08:47
Accommodation Informations / Дата Заезда
Guest Name / Имя Фамилия гостя  VICTOROV ANDREY - 03.03.1990 (35)
VIKTOROVA VASILISA - 22.07.1989 (35)
VIKTOROVA MILA - 01.12.2024 (0)
VIKTOROVA ALISA - 18.08.2024 (0)
Arrival Date / Дата Заезда  29.04.2025
Departure Date / Дата Выезда  04.05.2025
Nights / Количество Ночей  5
No. Of Adult / Количество взрослых  2
No. Of Baby / Количество младенцев (0-1)  2
Room Type / Тип номера  Family Land View Room
Board Type / Вид размещения  Ultra All Inclusive
No. of Room / Количество номеров  1
Notes / примечания
Guest Notes / Примечания гостя  Please note, kids 3 and 6 years old.! Correct dtes of birth for kids: Alisa - 18.08.2021 and Mila - 01.12.2018
Rate Informations / Информация о ценах
Total Amount / Общая сумма  1 319,65 EUR - ( 1 319,65   EUR )
Pre Payment Amount / Сумма предоплаты  1 319,65 EUR
Pre Payment Commission Amount / Сумма предоплаты  0,00 EUR
Pre Payment Date / Дата предоплаты
(СаналПос) Garanti - Dobedan(10081274) - ************0561 - 1 319,65 EUR - (11842) - (783638) - 27.04.2025, воскресенье (09:43)

---------- Дополнительные платежи----------
Used Bonus Amount / Используемая сумма бонуса  0,00 EUR !!
Extras / Дополнительно
"""

checkpointer = MemorySaver()

# Тестовый вызов нового графа.
context = AgentContext(
    model=model,
    tavily_client=TavilyClient(
        api_key=settings.tavily_api_key,
    ),
    bot=None,  # type: ignore[arg-type]  # email-граф не использует
    db_session=None,  # type: ignore[arg-type]  # email-граф не использует
    outbound_mail_gateway=None,  # type: ignore[arg-type]  # email-граф не использует
    user_id=1,
)
hotel_email_graph = get_email_graph(checkpointer)


async def run_graph() -> None:
    result = await hotel_email_graph.ainvoke(
        {
            "email_body": email_text,
            "request_id": str(uuid7()),
        },
        config={
            "configurable": {
                "thread_id": "test_thread_1",
            },
        },
        context=context,
    )
    print("\n=== graph result ===")
    pprint(result)


if __name__ == "__main__":
    asyncio.run(run_graph())
