"""Small, dependency-light helpers used by the agent's graph nodes.

These are deliberately kept out of :mod:`src.agent.agent` (the graph definition) so that file
reads as agent logic and these reusable pieces — Langfuse wiring, the Telegram typing indicator,
provider-specific model config — stand alone, each decoupled from :class:`EmailContext` /
:class:`Runtime` (they take primitives).
"""
