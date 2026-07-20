"""Auto-summarization of long conversations into a running summary.

When the model's input size (reported by the provider in ``usage_metadata``) crosses a soft
threshold, the ``summarize`` node ([src/agent/agent.py](src/agent/agent.py)) compresses the old
message prefix into a running ``conversation_summary`` and removes that prefix via
:class:`RemoveMessage` (the stock ``add_messages`` reducer drops entries by id). A recency window
of the most recent messages is always retained, and the split boundary never separates an
``AIMessage(tool_calls)`` from the ``ToolMessage``(s) that answer it.

Orthogonal to [src/agent/compaction.py](src/agent/compaction.py): compaction retires disposable
*search/extract tool output* at end of turn, in place; summarization retires the *conversation
history itself* when it grows past the context window. The two never interfere.

Pure helpers (:func:`summarization_needed`, :func:`split_index`) take/return plain data; only
:func:`summarize_prefix` performs the LLM call, building the model via :func:`src.llm.build_model`
(just like the model node — ``ApplicationContext`` carries no chat model). No live object is held in
agent state or ``EmailContext``, so the Temporal workflow↔activity boundary stays clean.
"""

from collections.abc import Sequence

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import Runnable

from src.agent.prompts import SYSTEM_MAIN, SYSTEM_SUMMARIZE

__all__ = ["split_index", "summarization_needed", "summarize_prefix"]


def summarization_needed(last_prompt_tokens: int, threshold: int) -> bool:
    """Reactive trigger: did the *previous* model call already exceed the soft threshold?

    The check runs against the past call's reported ``input_tokens`` (stored in
    ``EmailState.last_prompt_tokens``), so the very first model call of a conversation — which has
    no past usage to read — is never summarized.
    """
    return last_prompt_tokens > threshold


def _has_tool_calls(message: BaseMessage) -> bool:
    return isinstance(message, AIMessage) and bool(message.tool_calls)


def split_index(messages: Sequence[AnyMessage], keep_last: int) -> int:
    """Index at which to split ``messages`` into prefix (removed) and window (retained).

    The recency window is ``messages[cut:]``; the prefix summarized + removed is
    ``messages[:cut]``. ``keep_last`` is the desired window size; the cut is moved *back* whenever it
    would leave a ``ToolMessage`` in the window whose issuing ``AIMessage(tool_calls)`` fell into the
    prefix — a ``ToolMessage`` without its call breaks the provider's tool-call ↔ response linkage
    and the model with it. Over-conservative moves (keeping one extra message) are harmless; a split
    pair is not.
    """
    cut = max(0, len(messages) - keep_last)
    while cut > 0 and isinstance(messages[cut], ToolMessage) and _has_tool_calls(messages[cut - 1]):
        cut -= 1
    return cut


async def summarize_prefix(
    model: Runnable,
    prefix: Sequence[AnyMessage],
    prev_summary: str | None,
) -> str:
    """One-shot LLM compression of ``prefix`` into a running summary string.

    The caller ([src/agent/agent.py](src/agent/agent.py) ``summarize_node``) passes an
    already-configured model — built **identically** to ``model_node`` (same provider, same bound
    tools, same OpenRouter sticky session). The summarize call must be a cache *continuation* of the
    long thread, not a separate request: any difference in the model config (tools present/absent,
    ``session_id``) busts the prefix cache.

    **The prefix is immutable** (the project's cache rule). The message order mirrors ``model_node``
    exactly so the cached prefix carries over:

    - ``SYSTEM_MAIN`` — system prompt, first (never replaced by the summarization prompt).
    - ``SystemMessage(prev_summary)`` — the running summary in the *same position* ``model_node``
      injects it (right after ``SYSTEM_MAIN``), not at the end. At re-summarization ``prev_summary``
      equals exactly what ``model_node`` has been sending, so ``[SYSTEM_MAIN + summary + history]``
      is byte-identical to the cached prefix → cache hit.
    - ``*prefix`` — the old message history being compressed (a prefix of what ``model_node`` sent).
    - ``HumanMessage(SYSTEM_SUMMARIZE)`` — the summarization instruction, the **only** uncached part,
      appended last.

    Re-summarization accumulates: the prior summary is part of the cached prefix (as the
    ``SystemMessage``), and the freshly compressed prefix extends it.
    """
    history: list[AnyMessage] = [SYSTEM_MAIN]
    if prev_summary:
        history.append(SystemMessage(content=prev_summary))
    history.extend(prefix)
    history.append(HumanMessage(content=SYSTEM_SUMMARIZE.content))
    result = await model.ainvoke(history)
    return str(result.content)
