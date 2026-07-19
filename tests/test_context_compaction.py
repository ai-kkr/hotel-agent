"""Integration tests for end-of-turn context compaction (the ``cleanup`` node).

Drives a real turn through a compiled :class:`StateGraph(EmailState)` that reuses the production
``tool_path`` (routing + shortcut) and ``cleanup_node`` against the stock ``add_messages`` reducer.
The fake parts are the ``model`` node (canned :class:`AIMessage`s) and a thin ``tools`` node wrapper
that runs the *real* ``search_internet`` tool against a fake Tavily client (the search tool itself is
unchanged code, so its dependency is the right boundary to mock — same pattern as
[tests/test_scheduling.py](tests/test_scheduling.py)).
"""

import types
from collections.abc import AsyncIterator

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from src.agent.agent import cleanup_node, tool_path
from src.agent.compaction import ARCHIVABLE_TOOLS, ARCHIVED_KWARG, STUB_CONTENT
from src.agent.state import EmailState
from src.agent.tools.search import search_internet
from src.context import ApplicationContext, set_context

# A heavy payload the way Tavily would return one — this is exactly what compaction exists to retire.
_HEAVY_PAYLOAD = "contact@hotel.example\n" + ("x" * 8000)


class _FakeTavily:
    """Stand-in for :class:`tavily.tavily.TavilyClient` — ``search``/``extract`` return heavy text."""

    def search(self, query: str, **_: object) -> str:
        return _HEAVY_PAYLOAD

    def extract(self, url: str) -> dict:
        return {"raw_content": _HEAVY_PAYLOAD}


@pytest.fixture
async def fake_tavily() -> AsyncIterator[_FakeTavily]:
    """Wire a fake Tavily client into the process context (``search_internet`` reads it lazily)."""
    client = _FakeTavily()
    set_context(
        ApplicationContext(
            bot=None,  # type: ignore[arg-type]
            mailtrap_client=None,  # type: ignore[arg-type]
            session_factory=None,  # type: ignore[arg-type]
            tavily_client=client,  # type: ignore[arg-type]
        )
    )
    yield client


def _build_graph(model_script: list[AIMessage], tools_impl) -> "object":  # type: ignore[type-arg]
    """A graph mirroring ``build_email_agent``'s shape, with a scripted fake model + a tools node.

    Reuses the *real* ``tool_path`` (the shortcut decision) and the *real* ``cleanup_node`` and
    ``EmailState`` (so the stock ``add_messages`` reducer runs). The model node pops the next canned
    :class:`AIMessage`; the tools node runs the real ``search_internet``.
    """
    script = iter(model_script)

    async def model_node(state: EmailState) -> EmailState:
        return {"messages": [next(script)]}  # type: ignore[arg-type]

    g = StateGraph(state_schema=EmailState)  # type: ignore[arg-type]
    g.add_node("model", model_node)
    g.add_node("tools", tools_impl)
    g.add_node("cleanup", cleanup_node)
    g.add_edge(START, "model")
    g.add_conditional_edges("model", tool_path)
    g.add_edge("tools", "model")
    g.add_edge("cleanup", END)
    return g.compile()


async def _run_search_turn(tools_impl) -> EmailState:  # type: ignore[valid-type]
    """Turn 1: model calls ``search_internet``, then replies with no further tool calls."""
    graph = _build_graph(
        model_script=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_internet",
                        "args": {"query": "contact Hotel X"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Готово — нашёл email отеля."),
        ],
        tools_impl=tools_impl,
    )
    return await graph.ainvoke({"messages": [HumanMessage(content="найди контакт отеля")]})  # type: ignore[no-any-return]


# --- Tests ----------------------------------------------------------------------------


async def test_search_turn_compacts_heavy_tool_message(fake_tavily: _FakeTavily):
    """3.1: a turn that searched ends ``model → cleanup → END``; the heavy ToolMessage is replaced
    in place by a stub (same ``id`` / ``tool_call_id`` / ``name``, archived marker set, short content)."""

    async def tools_impl(state: EmailState) -> EmailState:
        # Run the REAL search tool; mimic ToolNode which sets ``message.name = call["name"]``
        # (langgraph/prebuilt/tool_node.py). Without that, the whitelist-by-name wouldn't match —
        # this is the production invariant the compaction relies on.
        runtime = types.SimpleNamespace(
            context=None,
            tool_call_id="c1",
            state={"search_rounds": 0},
        )
        cmd = await search_internet.coroutine(query="contact Hotel X", runtime=runtime)
        msg: ToolMessage = cmd.update["messages"][0]
        msg.name = "search_internet"
        return {"messages": [msg], "search_rounds": cmd.update["search_rounds"]}  # type: ignore[dict-item]

    result = await _run_search_turn(tools_impl)
    messages = result["messages"]

    search_msgs = [
        m for m in messages if isinstance(m, ToolMessage) and m.name == "search_internet"
    ]
    # In-place (id-upsert), not append: exactly one search ToolMessage after cleanup.
    assert len(search_msgs) == 1
    stub = search_msgs[0]
    assert stub.content == STUB_CONTENT["search_internet"]
    assert stub.additional_kwargs.get(ARCHIVED_KWARG) is True
    assert stub.tool_call_id == "c1"
    # The heavy payload is gone from history.
    assert not any(_HEAVY_PAYLOAD in str(m.content) for m in messages)
    # Sanity: the stub content really is short.
    assert len(stub.content) < 60


async def test_shortcut_skips_cleanup_when_nothing_archivable(fake_tavily: _FakeTavily):
    """3.2: when state holds only an already-archived stub, ``tool_path`` shortcuts straight to END
    (no cleanup), and the archived stub is untouched on a later turn."""

    archived_stub = ToolMessage(
        content=STUB_CONTENT["search_internet"],
        tool_call_id="c1",
        name="search_internet",
        additional_kwargs={ARCHIVED_KWARG: True},
    )
    state = {  # type: ignore[var-annotated]
        "messages": [
            HumanMessage(content="найди контакт отеля"),
            AIMessage(
                content="ищу…",
                tool_calls=[
                    {"name": "search_internet", "args": {}, "id": "c1", "type": "tool_call"}
                ],
            ),
            archived_stub,
            AIMessage(content="Готово."),
        ]
    }
    # Shortcut decision: nothing un-archived → END, no cleanup node.
    assert await tool_path(state) == "__end__"  # type: ignore[arg-type]

    # And running a no-tool-calls turn through the graph leaves the stub exactly as it was. The tools
    # node is wired (so the graph compiles — ``tool_path`` declares it as a branch target) but never
    # reached, because the model emits no tool calls.
    async def idle_tools(state: EmailState) -> EmailState:
        raise AssertionError("tools node must not run on a no-tool-calls turn")

    graph = _build_graph(model_script=[AIMessage(content="Чем ещё помочь?")], tools_impl=idle_tools)
    result = await graph.ainvoke(state)  # type: ignore[arg-type]
    stubs = [
        m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == "search_internet"
    ]
    assert len(stubs) == 1
    assert stubs[0].content == STUB_CONTENT["search_internet"]
    assert stubs[0].additional_kwargs.get(ARCHIVED_KWARG) is True


async def test_non_whitelisted_long_message_is_preserved(fake_tavily: _FakeTavily):
    """3.3: a long non-whitelisted message (an inbound hotel reply) is preserved verbatim through
    cleanup — compaction is selected by ``ToolMessage.name`` ∈ ARCHIVABLE_TOOLS, never by size."""

    long_hotel_reply = HumanMessage(content=("Здравствуйте, подтверждаем ранний заезд. " * 200))

    async def tools_impl(state: EmailState) -> EmailState:
        runtime = types.SimpleNamespace(context=None, tool_call_id="c1", state={"search_rounds": 0})
        cmd = await search_internet.coroutine(query="contact Hotel X", runtime=runtime)
        msg: ToolMessage = cmd.update["messages"][0]
        msg.name = "search_internet"
        return {"messages": [msg], "search_rounds": cmd.update["search_rounds"]}  # type: ignore[dict-item]

    # Seed the turn with the long hotel reply already in history.
    graph = _build_graph(
        model_script=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_internet",
                        "args": {"query": "contact Hotel X"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Готово."),
        ],
        tools_impl=tools_impl,
    )
    result = await graph.ainvoke(
        {"messages": [long_hotel_reply, HumanMessage(content="найди контакт")]}
    )  # type: ignore[no-any-return]

    # The hotel reply survives unchanged; the search result was compacted.
    human_contents = [m.content for m in result["messages"] if isinstance(m, HumanMessage)]
    assert long_hotel_reply.content in human_contents
    assert any(
        isinstance(m, ToolMessage)
        and m.name == "search_internet"
        and m.additional_kwargs.get(ARCHIVED_KWARG)
        for m in result["messages"]
    )
    # Whitelist itself is exactly the two disposable search/extract tools.
    assert frozenset({"search_internet", "extract_web_page"}) == ARCHIVABLE_TOOLS
