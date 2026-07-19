"""End-of-turn compaction of disposable search/extract tool output.

``search_internet`` and ``extract_web_page`` ([src/agent/tools/search.py](src/agent/tools/search.py))
drop full Tavily payloads into ``EmailState.messages`` as :class:`ToolMessage`s. Those blobs are
persisted (JSONB ``states``) and re-sent to the model on every subsequent turn of the same client
thread, even though the agent already pulled what it needed into the structured booking fields.

This module produces *stubs* that replace the heavy content **in place** via the stock
``add_messages`` reducer's ID-based upsert (same ``id`` ⇒ overwrite) — see the ``cleanup`` node in
[src/agent/agent.py](src/agent/agent.py). Each stub reuses the original ``id`` / ``tool_call_id`` /
``name`` so the provider's tool-call ↔ tool-response linkage and LangGraph's bookkeeping stay intact,
and carries ``additional_kwargs["archived"] = True`` so it is never re-processed.

Pure data in / pure data out — no live objects, no ``get_context()``, no LLM.
"""

from collections.abc import Sequence

from langchain_core.messages import AnyMessage, BaseMessage, ToolMessage

__all__ = [
    "ARCHIVABLE_TOOLS",
    "ARCHIVED_KWARG",
    "STUB_CONTENT",
    "compact",
    "compaction_needed",
]

#: Tools whose :class:`ToolMessage` output is disposable after the turn that produced it. Matching is
#: by ``ToolMessage.name`` (which :class:`~langgraph.prebuilt.ToolNode` sets from the tool-call name),
#: never by content size — a long hotel reply must never be compacted.
ARCHIVABLE_TOOLS: frozenset[str] = frozenset({"search_internet", "extract_web_page"})

#: Marker stored in ``ToolMessage.additional_kwargs`` on a stub so the cleanup node skips it on
#: later turns. A plain-dict kwarg that already round-trips through ``messages_to_dict`` /
#: ``messages_from_dict`` (``StateType``) and ``message_aware_data_converter`` — no schema change.
ARCHIVED_KWARG: str = "archived"

#: Per-tool stub content (short fixed string — no LLM digest).
STUB_CONTENT: dict[str, str] = {
    "search_internet": "[архив: результаты поиска]",
    "extract_web_page": "[архив: текст страницы]",
}

#: Fallback stub content for any future whitelisted tool without an explicit entry.
_DEFAULT_STUB: str = "[архив]"


def _is_archivable(message: BaseMessage) -> bool:
    return (
        isinstance(message, ToolMessage)
        and message.name in ARCHIVABLE_TOOLS
        and not message.additional_kwargs.get(ARCHIVED_KWARG)
    )


def compaction_needed(messages: Sequence[AnyMessage]) -> bool:
    """Shortcut predicate: is there at least one un-archived archivable ``ToolMessage``?"""
    return any(_is_archivable(m) for m in messages)


def compact(messages: Sequence[AnyMessage]) -> list[AnyMessage]:
    """Build replacement stubs for every un-archived archivable ``ToolMessage``.

    Returns only the stubs to emit (the ``add_messages`` reducer upserts each in place by ``id``).
    Empty list when there is nothing to compact — feeding an empty list to the reducer is a no-op.
    """
    stubs: list[AnyMessage] = []
    for message in messages:
        # Inline the archivable check so the static type narrows to ``ToolMessage`` (a helper
        # predicate would not, and ``tool_call_id`` / ``name`` / ``id`` live only on it).
        if (
            not isinstance(message, ToolMessage)
            or message.name not in ARCHIVABLE_TOOLS
            or message.additional_kwargs.get(ARCHIVED_KWARG)
        ):
            continue
        stubs.append(
            ToolMessage(
                content=STUB_CONTENT.get(message.name, _DEFAULT_STUB),
                tool_call_id=message.tool_call_id,
                name=message.name,
                id=message.id,
                additional_kwargs={ARCHIVED_KWARG: True},
            )
        )
    return stubs
