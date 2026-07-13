"""Application configuration (pydantic-settings).

All environment-driven knobs live here. Adapter selection (mail provider) is a config value so
swapping providers is a deployment concern, not a code change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MailProvider = Literal["mailgun", "custom", "stub"]


class Settings(BaseSettings):
    """Runtime configuration, sourced from environment (prefix ``KKR_``) or a ``.env`` file."""

    model_config = SettingsConfigDict(env_prefix="KKR_", env_file=".env", extra="ignore")

    #
    is_dev: bool = True
    # --- Mail provider / Mailgun (v1) ---
    mail_provider: MailProvider = "mailgun"
    mail_domain: str = "kkr-hotel.com"
    mailgun_base_url: str = "https://api.mailgun.net"
    mailgun_api_key: str = ""
    mailgun_signing_key: str = ""

    # --- Postgres ---
    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kkr"
    # PostgresSaver uses psycopg (sync driver); may point at the same DB.
    langgraph_dsn: str = "postgresql://postgres:postgres@localhost:5432/kkr"

    # --- Temporal ---
    temporal_target: str = "localhost:7233"
    temporal_task_queue: str = "kkr-hotel"

    # --- Negotiation timing ---
    hotel_reply_timeout_seconds: int = Field(default=2 * 24 * 3600, ge=60)
    followup_max_attempts: int = Field(default=2, ge=0)
    # How long to wait for a client to clarify a low-confidence / incomplete extraction.
    clarify_timeout_seconds: int = Field(default=14 * 24 * 3600, ge=60)
    # How long a finalized booking waits for a client follow-up before going dormant (design D11).
    reactivation_timeout_seconds: int = Field(default=30 * 24 * 3600, ge=60)
    # Continue-As-New threshold: max negotiation agent-turns per workflow run before history reset.
    workflow_continue_as_new_threshold: int = Field(default=5, ge=0)
    # start_to_close_timeout for LLM-backed activities (extract, agent_turn).
    llm_activity_timeout_seconds: int = Field(default=180, ge=1)

    # --- Extraction ---
    extraction_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # --- LLM ---
    # ``llm_model`` is "<provider>:<name>" (e.g. "openai:gpt-4o-mini", "zai:glm-5.2") or a bare name
    # (provider inferred as openai). See ``src.llm.build_model``.
    llm_model: str = "gpt-4o-mini"
    # Z.AI / Zhipu GLM provider (OpenAI-compatible). Used when llm_model is "zai:<model>".
    # Default base_url points at the **Coding Plan** OpenAI-compatible endpoint (billed against the
    # subscription, NOT the pay-as-you-go PaaS balance). Override KKR_ZAI_API_BASE to switch platforms
    # or protocols (e.g. https://api.z.ai/api/paas/v4/ for international PaaS credits).
    zai_api_key: str = ""
    zai_api_base: str = "https://open.bigmodel.cn/api/coding/paas/v4"
    # OpenRouter (OpenAI-compatible aggregator). Used when llm_model is "openrouter:<model>".
    # Model name should include the vendor prefix as OpenRouter expects (e.g. "anthropic/claude-3.5-sonnet").
    openrouter_api_key: str = ""
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    # OpenRouter reasoning/thinking effort, applied only for the ``openrouter:`` provider.
    # OpenRouter enum (maps to per-model settings, e.g. Gemini ``thinkingLevel``):
    # ``xhigh | high | medium | low | minimal | none``. ``minimal`` = least thinking while still
    # reasoning; ``none`` disables reasoning entirely where the model supports it.
    # ``None`` leaves the provider default. See https://openrouter.ai/docs/api/reference/parameters.
    openrouter_reasoning_effort: str | None = "minimal"

    # --- Outbound report delivery channel (v1 = email) ---
    client_channel: Literal["email"] = "email"

    # --- Telegram bot / bot-facing API (design D10) ---
    # Shared secret authenticating the bot → API calls (POST /api/client-mailbox). Not user creds.
    bot_api_secret: str = ""
    # Telegram bot token (polling/webhook). Empty disables the adapter.
    telegram_bot_token: str = ""
    telegram_polling: bool = True  # True = long-poll; False = webhook (url configured out-of-band)
    # Server-side long-poll seconds for getUpdates (HTTP read timeout is padded beyond this).
    telegram_poll_timeout_seconds: int = Field(default=30, ge=1)

    # --- Langfuse (LLM observability; self-hosted via docker compose) ---
    # Tracing is OFF unless explicitly enabled AND keys are present, so local/test runs without
    # the Langfuse stack stay clean. Keys must match LANGFUSE_INIT_PROJECT_* from the compose file.
    langfuse_enabled: bool = False
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    # mailtrap integration (inbound webhook) for local development / testing. In production, inbound
    mailtrap_api_key: str = ""
    mailtrap_signing_secret: str = ""
    mailtrap_inbox_id: int = 0
    mailtrap_base_url: str = "https://mailtrap.io"
    # Verified Mailtrap sending address used as the ``From`` for outbound mail (must be on a
    # domain verified under Mailtrap Email API → Sending Domains; the inbound inbox address is
    # not allowed as a sender and yields 401 Unauthorized).
    mailtrap_from_email: str = ""
    # tavily
    tavily_api_key: str = ""


def get_settings() -> Settings:
    """Return a fresh :class:`Settings` instance."""
    return Settings()
