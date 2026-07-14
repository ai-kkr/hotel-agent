"""Application configuration (pydantic-settings).

All environment-driven knobs live here. Configuration is loaded from (later sources win, so
earlier in the list = higher priority):

1. constructor kwargs
2. environment variables (prefix ``KKR_``) — best for secrets / per-deploy overrides
3. ``.env`` file
4. optional YAML file (``KKR_CONFIG_FILE``, default ``config.yaml``) — best for structured,
   version-controlled tuning (LLM timeouts, per-tool retry policies, …)
5. field defaults

The truth-of-the-source for any setting is this module; the YAML file mirrors field names.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

MailProvider = Literal["mailgun", "custom", "stub"]


class ToolRetryPolicy(BaseModel):
    """Retry policy for a single tool (or the default applied to unnamed tools).

    ``retry_on`` selects which exceptions are retried:

    - ``"transient"`` (default): retry on anything that is *not* a deterministic/logic error
      (``SelfCorrectionError``, ``ValueError``, ``TypeError``, …). Network blips get retried;
      precondition/logic failures surface immediately.
    - ``"all"``: retry on every exception except ``SelfCorrectionError`` (which is handled by
      :class:`SelfCorrectionMiddleware` and must never be retried).
    """

    max_retries: int = Field(default=0, ge=0)
    backoff_factor: float = Field(default=2.0, ge=0.0)
    initial_delay: float = Field(default=1.0, ge=0.0)
    max_delay: float = Field(default=30.0, ge=0.0)
    jitter: bool = True
    retry_on: Literal["transient", "all"] = "transient"


class ToolRetryConfig(BaseModel):
    """Per-tool retry configuration.

    ``default`` is the fallback for any tool not listed in ``overrides``; ``overrides`` maps a
    tool name (as the agent calls it, e.g. ``send_wishes_to_hotel``) to its own policy.
    """

    default: ToolRetryPolicy = Field(default_factory=ToolRetryPolicy)
    overrides: dict[str, ToolRetryPolicy] = Field(default_factory=dict)


_DEFAULT_YAML_PATH = "config.yaml"


class Settings(BaseSettings):
    """Runtime configuration, sourced from environment (prefix ``KKR_``) or a ``.env`` file."""

    model_config = SettingsConfigDict(
        env_prefix="KKR_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Layer env > .env > YAML > defaults.

        The YAML path is read straight from the environment (``KKR_CONFIG_FILE``, default
        ``config.yaml``) rather than from a parsed field, to avoid the chicken-and-egg of needing
        a fully constructed :class:`Settings` to know which file to load. A missing file is
        silently skipped, so runs without one stay clean.
        """
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,
            env_settings,
            dotenv_settings,
        ]
        yaml_path = os.environ.get("KKR_CONFIG_FILE") or _DEFAULT_YAML_PATH
        if os.path.exists(yaml_path):
            sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path))
        return tuple(sources)

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
    # Per-request timeout (seconds) applied to every chat-model call — both the agent's model node
    # and the direct ``model.ainvoke`` in ``_compose_letter``. ``0`` = no timeout (let the provider
    # decide). Passed as ``timeout=`` to the langchain chat model.
    llm_timeout_seconds: float = Field(default=60.0, ge=0.0)
    # Max retry attempts on a failed chat-model HTTP call (timeouts, 5xx, transport errors).
    # Applied at the provider client level, so it also covers ``_compose_letter``. ``0`` = no retry.
    llm_max_retries: int = Field(default=3, ge=0)
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

    # --- Tool retry policy ---
    # Per-tool retry behaviour, applied by :class:`ToolRetryMiddleware`. Defaults are conservative:
    # the catch-all default does not retry, and each tool is given an explicit policy in
    # ``config.yaml`` (sending tools never retry, network tools do).
    tool_retry: ToolRetryConfig = Field(default_factory=ToolRetryConfig)

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

    # --- Optional YAML config file (``KKR_CONFIG_FILE`` overrides). Pure metadata: the path is
    # actually read in :meth:`settings_customise_sources` before fields are parsed. ---
    config_file: str = _DEFAULT_YAML_PATH

    def tool_retry_policy(self, tool_name: str) -> ToolRetryPolicy:
        """Resolve the retry policy for ``tool_name``, falling back to the default."""
        return self.tool_retry.overrides.get(tool_name, self.tool_retry.default)


def get_settings() -> Settings:
    """Return a fresh :class:`Settings` instance."""
    return Settings()
