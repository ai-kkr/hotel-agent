"""Integration tests for conversation auto-summarization (the ``summarize`` node).

Drives a compiled :class:`StateGraph(EmailState)` mirroring ``build_email_agent``'s entry routing
(``START → summarize_check → summarize → model``) against the *production* ``summarize_check`` and
``summarize_node`` and the stock ``add_messages`` reducer. The mocked boundaries are the chat model
(a scripted fake, patched in where ``summarize_prefix`` builds it) and the Telegram push (a no-op
patch, so the node runs without a bot/runtime). ``split_index`` and ``summarize_prefix`` are also
exercised directly for the tool-call guard and the cache-aware call shaping.
"""

from collections.abc import AsyncIterator

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from src.agent import agent as agent_mod
from src.agent.agent import summarize_check, summarize_node
from src.agent.context import EmailContext
from src.agent.prompts import SYSTEM_MAIN, SYSTEM_SUMMARIZE
from src.agent.state import EmailState
from src.agent.summarization import split_index, summarize_prefix

# Default threshold from config (summarize_token_threshold = 100000).
_OVER = 200_000
_UNDER = 100


class _FakeModel:
    """Stand-in chat model: records every ainvoke input, returns a canned :class:`AIMessage`.

    ``bind_tools`` returns ``self`` — the production ``summarize_node`` binds tools for cache-parity
    with ``model_node``; the fake just needs to stay usable through that call.
    """

    def __init__(self, reply: str = "СВОДКА") -> None:
        self.reply = reply
        self.inputs: list[list] = []

    def bind_tools(self, *_: object, **__: object) -> "_FakeModel":
        return self

    async def ainvoke(self, messages, **_: object):  # type: ignore[no-untyped-def]
        self.inputs.append(list(messages))
        return AIMessage(content=self.reply)


@pytest.fixture
async def fake_model(monkeypatch) -> AsyncIterator[_FakeModel]:
    """Patch ``build_model`` inside the agent module so ``summarize_node`` uses the fake (tools-bound)."""
    model = _FakeModel()
    monkeypatch.setattr(agent_mod, "build_model", lambda _settings: model)
    yield model


@pytest.fixture(autouse=True)
def _no_telegram_push(monkeypatch):
    """Suppress the guest-notification push — ``summarize_node`` runs without a Telegram bot/runtime
    in a plain compiled graph. (Langfuse needs no patch: ``inject_langfuse_callback`` handles the
    ``AsyncCallbackManager`` callbacks a plain ``ainvoke`` sets.)"""

    async def _noop(_content: str) -> None:
        return None

    monkeypatch.setattr(agent_mod, "send_telegram_reply", _noop)


# Context passed to the test graph so the production ``summarize_node`` (which reads the client id
# off ``runtime.context`` for the sticky session) gets a runtime injection.
_CTX: dict = {"client_id": 1}


def _build_graph(model_replies: list[AIMessage], capture: list) -> object:  # type: ignore[type-arg]
    """A graph mirroring ``build_email_agent``'s entry side, with a scripted fake model node.

    The fake model node mirrors the production ``model_node`` summary-prepending (read
    ``conversation_summary``, inject it as a :class:`SystemMessage` right after ``SYSTEM_MAIN``) so
    the test can assert the summary actually reaches the model after summarization. Routing uses the
    *real* ``summarize_check`` and ``summarize_node``. ``context_schema=EmailContext`` lets
    ``summarize_node`` receive ``runtime`` (it needs the client id for the OpenRouter sticky session).
    """
    script = iter(model_replies)

    async def fake_model(state: EmailState) -> EmailState:
        summary = state.get("conversation_summary")
        invoke_input = (
            [SYSTEM_MAIN, SystemMessage(content=summary), *state["messages"]]
            if summary
            else [SYSTEM_MAIN, *state["messages"]]
        )
        capture.append(invoke_input)
        return {"messages": [next(script)]}  # type: ignore[arg-type]

    g = StateGraph(  # type: ignore[arg-type]
        state_schema=EmailState,
        context_schema=EmailContext,
    )
    g.add_node("model", fake_model)
    g.add_node("summarize", summarize_node)
    g.add_conditional_edges(START, summarize_check)
    g.add_edge("summarize", "model")
    g.add_edge("model", END)
    return g.compile()


# --- Tests ---------------------------------------------------------------------------


async def test_over_threshold_routes_through_summarize(fake_model: _FakeModel):
    """1: over-threshold ``last_prompt_tokens`` routes ``summarize_check → summarize → model``;
    the prefix is removed via ``RemoveMessage``, the recency window is retained, ``conversation_summary``
    is set, and the following model invoke sees the summary prepended plus the reduced history."""

    msgs = [HumanMessage(content=f"msg {i}", id=f"h{i}") for i in range(12)]  # keep_last=6
    capture: list = []
    graph = _build_graph([AIMessage(content="done", id="m0")], capture)

    result = await graph.ainvoke({"messages": msgs, "last_prompt_tokens": _OVER}, context=_CTX)  # type: ignore[arg-type]

    # summarize ran: conversation_summary holds the fake summarize-model reply.
    assert result["conversation_summary"] == "СВОДКА"
    # RemoveMessage dropped the prefix (h0..h5); the recency window (h6..h11) survives + model reply.
    remaining_ids = [m.id for m in result["messages"]]  # type: ignore[union-attr]
    assert "h0" not in remaining_ids and "h5" not in remaining_ids
    assert "h6" in remaining_ids and "h11" in remaining_ids
    # The summarize-prefix LLM call happened exactly once.
    assert len(fake_model.inputs) == 1
    # The following model invoke got [SYSTEM_MAIN, SystemMessage(summary), *window] — summary prepended,
    # reduced history (no removed prefix).
    model_input = capture[0]
    assert model_input[0] is SYSTEM_MAIN
    assert any(isinstance(m, SystemMessage) and m.content == "СВОДКА" for m in model_input)
    assert "h0" not in [getattr(m, "id", None) for m in model_input]


async def test_under_threshold_skips_summarize(fake_model: _FakeModel):
    """2: under-threshold ``last_prompt_tokens`` routes ``summarize_check → model`` directly — no
    summarize activity is scheduled (the summarize model is never invoked) and history is untouched."""

    msgs = [HumanMessage(content="hi", id="h0"), AIMessage(content="hello", id="a0")]
    capture: list = []
    graph = _build_graph([AIMessage(content="ok", id="m0")], capture)

    result = await graph.ainvoke({"messages": msgs, "last_prompt_tokens": _UNDER}, context=_CTX)  # type: ignore[arg-type]

    assert not result.get("conversation_summary")  # summarize never ran
    assert fake_model.inputs == []  # the summarize-prefix LLM call never happened
    assert [m.id for m in result["messages"]] == ["h0", "a0", "m0"]  # type: ignore[union-attr]


async def test_first_call_has_no_signal_so_it_is_not_summarized(fake_model: _FakeModel):
    """The first model call of a conversation has no past usage (``last_prompt_tokens`` absent) →
    ``summarize_check`` routes straight to the model."""

    capture: list = []
    graph = _build_graph([AIMessage(content="ok", id="m0")], capture)
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="first", id="h0")]}, context=_CTX
    )  # type: ignore[arg-type]
    assert fake_model.inputs == []
    assert not result.get("conversation_summary")


async def test_async_start_branch_works_with_aupdate_state():
    """Regression: the Temporal LangGraph plugin seeds state inside an async workflow via
    ``g.aupdate_state`` ([src/temporal/agent_runner.py](src/temporal/agent_runner.py)). The entry
    branch (``summarize_check``) is async, like every node — so the caller MUST use the async
    ``aupdate_state`` (not the sync ``update_state``, which drives a sync superstep that can't await
    an async branch → ``TypeError: No synchronous function provided``). This compiles the graph with a
    checkpointer and calls ``aupdate_state`` the way the plugin does; the async branch must resolve
    cleanly."""

    from langgraph.checkpoint.memory import InMemorySaver

    async def fake_model(state: EmailState) -> EmailState:
        return {"messages": [AIMessage(content="ok", id="m0")]}

    g = StateGraph(state_schema=EmailState, context_schema=EmailContext)  # type: ignore[arg-type]
    g.add_node("model", fake_model)
    g.add_node("summarize", summarize_node)
    g.add_conditional_edges(START, summarize_check)
    g.add_edge("summarize", "model")
    g.add_edge("model", END)
    graph = g.compile(checkpointer=InMemorySaver())

    # Mirrors src/temporal/agent_runner.py run_user → await g.aupdate_state(...). Must not raise.
    await graph.aupdate_state(
        config={"configurable": {"thread_id": "t1"}},
        values={"messages": [HumanMessage(content="seed", id="s")], "last_prompt_tokens": 50},
    )
    # And the branch is async, like the other nodes (the invariant the caller relies on).
    import inspect

    assert inspect.iscoroutinefunction(summarize_check)


def test_split_index_never_breaks_a_tool_call_pair():
    """3: the recency cut is moved back when it would leave a ``ToolMessage`` in the window whose
    issuing ``AIMessage(tool_calls)`` fell into the prefix — the pair stays together."""

    msgs = [
        HumanMessage(content="q", id="0"),
        AIMessage(content="a1", id="1"),
        HumanMessage(content="q2", id="2"),
        AIMessage(
            content="",
            tool_calls=[{"name": "t", "args": {}, "id": "c1", "type": "tool_call"}],
            id="3",
        ),
        ToolMessage(content="r", tool_call_id="c1", id="4"),
        HumanMessage(content="q3", id="5"),
        AIMessage(content="final", id="6"),
    ]
    # len=7, keep_last=3 → naive cut=4 (a ToolMessage) right after the AIMessage(tool_calls) at [3].
    cut = split_index(msgs, keep_last=3)
    assert (
        cut == 3
    )  # moved back so the AIMessage(tool_calls) stays in the window with its ToolMessage
    window = msgs[cut:]
    assert any(isinstance(m, AIMessage) and m.tool_calls for m in window)
    assert any(isinstance(m, ToolMessage) for m in window)


async def test_summarize_prefix_is_cache_aware_and_accumulates(fake_model: _FakeModel):
    """4: the prefix is immutable. ``SYSTEM_MAIN`` stays the system prompt and the prior summary rides
    as a :class:`SystemMessage` right after it — the *same position* ``model_node`` injects the running
    summary — so at re-summarization ``[SYSTEM_MAIN + summary + history]`` is byte-identical to the
    cached long-thread prefix (cache hit). The summarization instruction is the only uncached part, a
    trailing :class:`HumanMessage`."""

    prefix = [
        HumanMessage(content="old turn", id="p0"),
        AIMessage(content="old reply", id="p1"),
    ]
    out = await summarize_prefix(fake_model, prefix, "ПРЕДЫДУЩЕЕ")
    assert out == "СВОДКА"

    sent = fake_model.inputs[0]
    # [SYSTEM_MAIN, SystemMessage(prev_summary), *prefix, HumanMessage(instruction)]
    assert sent[0] is SYSTEM_MAIN
    assert (
        isinstance(sent[1], SystemMessage) and sent[1].content == "ПРЕДЫДУЩЕЕ"
    )  # front, like model_node
    assert sent[2] is prefix[0] and sent[3] is prefix[1]  # history follows, unchanged (cache-hit)
    last = sent[-1]
    assert isinstance(last, HumanMessage)
    assert SYSTEM_SUMMARIZE.content in last.content  # the instruction is the only uncached part
    assert (
        "ПРЕДЫДУЩЕЕ" not in last.content
    )  # prior summary is NOT in the trailing message — it's at front
    # No extra system messages beyond SYSTEM_MAIN + the prev-summary one (prefix has none).
    assert sum(isinstance(m, SystemMessage) for m in sent) == 2


async def test_summarize_prefix_without_prev_summary_matches_model_node_no_summary(
    fake_model: _FakeModel,
):
    """5: with no prior summary the shape is ``[SYSTEM_MAIN, *prefix, HumanMessage(instruction)]`` —
    the same prefix ``model_node`` sends before the first summarization (no summary SystemMessage)."""

    prefix = [HumanMessage(content="turn", id="p0")]
    await summarize_prefix(fake_model, prefix, None)
    sent = fake_model.inputs[0]
    assert sent[0] is SYSTEM_MAIN
    assert sent[1] is prefix[0]
    assert isinstance(sent[-1], HumanMessage)
    assert sum(isinstance(m, SystemMessage) for m in sent) == 1  # only SYSTEM_MAIN
