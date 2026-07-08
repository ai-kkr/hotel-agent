"""Collect a diverse corpus of forwarded hotel-booking confirmations from the owner's Gmail.

Pipeline (design D1-D6): ezgmail search -> one batch structured-output classification ->
first-seen-per-system selection → forward re-wrap → ``.eml`` + ``manifest.json`` to disk.

Run with::

    uv run python -m scripts.collect_corpus --help

The LLM model is built via the project's existing config (``infrastructure.agents.models``);
Gmail credentials are dev-local (see ``scripts/README.md``).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from langchain_core.language_models import BaseChatModel

from scripts.classifier import ConfirmationClassifier
from scripts.corpus_writer import write_corpus
from scripts.gmail_source import CorpusSource, GmailSource
from scripts.selector import select_diverse
from scripts.types import RunSummary

logger = logging.getLogger(__name__)

DEFAULT_QUERY = (
    'subject:(booking OR reservation OR confirmation OR "подтверждение" OR "бронир")'
    " -category:promotions -category:updates"
)
DEFAULT_OUT_DIR = Path.home() / ".kkr-hotel-corpus"


def collect(
    *,
    source: CorpusSource,
    model: BaseChatModel,
    query: str,
    count: int,
    client_email: str,
    recipient: str,
    out_dir: Path,
    confidence_threshold: float = 0.6,
    wishes_mode: str = "mixed",
    search_limit: int = 50,
) -> RunSummary:
    """Run the full collection pipeline. Network-free if ``source``/``model`` are fakes."""
    candidates = source.search(query, limit=search_limit)
    logger.info("found %d candidates for query", len(candidates))

    classifier = ConfirmationClassifier(model, confidence_threshold=confidence_threshold)
    classified = asyncio.run(classifier.classify(candidates))
    confirmed = [c for c in classified if c.is_hotel_confirmation]
    skipped = [c for c in classified if not c.is_hotel_confirmation]
    logger.info(
        "confirmed %d, skipped %d, unique systems=%d",
        len(confirmed),
        len(skipped),
        len({c.system for c in confirmed}),
    )

    selected = select_diverse(classified, count=count)
    result = write_corpus(
        selected,
        out_dir=out_dir,
        client_email=client_email,
        recipient=recipient,
        wishes_mode=wishes_mode,
    )
    logger.info("selected %d, wrote %d files to %s", len(selected), len(result.written_files), out_dir)

    return RunSummary(
        candidates_found=len(candidates),
        confirmed=len(confirmed),
        skipped=len(skipped),
        unique_systems=result.unique_systems,
        selected=len(selected),
        written_files=result.written_files,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect a diverse corpus of forwarded hotel-booking confirmations from your Gmail.",
    )
    parser.add_argument("--count", type=int, default=int(os.environ.get("KKR_CORPUS_COUNT", "10")))
    parser.add_argument("--query", default=os.environ.get("KKR_CORPUS_QUERY", DEFAULT_QUERY))
    parser.add_argument("--client-email", default=os.environ.get("KKR_CLIENT_EMAIL", ""))
    parser.add_argument(
        "--recipient",
        default=os.environ.get("KKR_CORPUS_RECIPIENT", "c.demo@kkr-hotel.com"),
        help="The c.<token>@<mail-domain> address these forwards are addressed to.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(os.environ.get("KKR_CORPUS_OUT", str(DEFAULT_OUT_DIR))),
    )
    parser.add_argument(
        "--confidence-threshold", type=float, default=float(os.environ.get("KKR_CONFIDENCE", "0.6"))
    )
    parser.add_argument(
        "--wishes", choices=("none", "mixed"), default=os.environ.get("KKR_CORPUS_WISHES", "mixed")
    )
    parser.add_argument(
        "--credentials",
        default=os.environ.get("KKR_GMAIL_CREDENTIALS", "credentials.json"),
        help="OAuth Desktop credentials.json from Google Cloud Console.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("KKR_GMAIL_TOKEN", "token.json"),
        help="Where ezgmail stores the refresh token after first consent.",
    )
    parser.add_argument(
        "--auth-port",
        type=int,
        default=int(os.environ.get("KKR_GMAIL_AUTH_PORT", "8411")),
        help="Local OAuth callback port. Default 8411 to avoid the 8080 temporal-ui collision.",
    )
    parser.add_argument("--search-limit", type=int, default=50)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # Quiet the chatty third-party OAuth/API loggers (e.g. "file_cache is only supported with
    # oauth2client<4.0.0"); our own `scripts.*` loggers stay at INFO.
    for noisy in ("googleapiclient", "googleapiclient.discovery_cache", "oauth2client", "google_auth_httplib2"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    args = _build_arg_parser().parse_args(argv)

    if not args.client_email:
        logger.error("--client-email (or KKR_CLIENT_EMAIL) is required — your registered client address")
        return 2

    source = GmailSource(
        credentials_path=args.credentials, token_path=args.token, auth_port=args.auth_port
    )
    model = _build_model()

    collect(
        source=source,
        model=model,
        query=args.query,
        count=args.count,
        client_email=args.client_email,
        recipient=args.recipient,
        out_dir=args.out_dir,
        confidence_threshold=args.confidence_threshold,
        wishes_mode=args.wishes,
        search_limit=args.search_limit,
    )
    return 0


def _build_model() -> BaseChatModel:
    # Uses the project's production model factory + config (KKR_LLM_MODEL, etc.).
    from infrastructure.agents.models import build_model
    from infrastructure.config import get_settings

    return build_model(get_settings())


if __name__ == "__main__":
    sys.exit(main())
