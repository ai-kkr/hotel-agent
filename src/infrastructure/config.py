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
    # (provider inferred as openai). See ``infrastructure.agents.models.build_model``.
    llm_model: str = "gpt-4o-mini"
    # Z.AI / Zhipu GLM provider (OpenAI-compatible). Used when llm_model is "zai:<model>".
    # Default base_url points at the **Coding Plan** OpenAI-compatible endpoint (billed against the
    # subscription, NOT the pay-as-you-go PaaS balance). Override KKR_ZAI_API_BASE to switch platforms
    # or protocols (e.g. https://api.z.ai/api/paas/v4/ for international PaaS credits).
    zai_api_key: str = ""
    zai_api_base: str = "https://open.bigmodel.cn/api/coding/paas/v4"

    # --- Outbound report delivery channel (v1 = email) ---
    client_channel: Literal["email"] = "email"


def get_settings() -> Settings:
    """Return a fresh :class:`Settings` instance."""
    return Settings()
