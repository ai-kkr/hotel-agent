"""Generate Mailtrap API clients (pydantic v2 + httpx) from the official OpenAPI specs.

This is a dev-only tool (see ``scripts/README.md``). It is NOT imported by production code.

What it does
------------
Mailtrap publishes OpenAPI 3.1 specs at https://github.com/mailtrap/mailtrap-openapi. We vendor
those spec files (see ``scripts/_vendor/mailtrap-openapi/``) and feed each one to
``openapi-python-client``, which emits a fully typed package: pydantic v2 models + httpx-based
sync/async clients with one method per endpoint. The ``from`` reserved word (used by the message
payload) is auto-aliased to ``from_``; datetimes, attachments and discriminated unions are typed.

We generate two packages from two specs:

* ``mailtrap_inbound``  <- ``inbound.openapi.yml``                       (folders, inboxes, received messages)
* ``mailtrap_sending``  <- ``email-sending.openapi.yml``                 (domains, suppressions, stats, logs)
* ``mailtrap_send``     <- ``email-sending-transactional.openapi.yml``   (transactional email sending, send.api)

Generated packages are committed to the repo as source so the app never depends on a generator
running at build time. Re-run this script when you want to pick up spec changes.

Usage
-----
    uv run python scripts/generate_mailtrap_client.py              # sync specs + (re)generate all
    uv run python scripts/generate_mailtrap_client.py sync         # only refresh vendored specs
    uv run python scripts/generate_mailtrap_client.py generate     # only regenerate from vendored specs
    uv run python scripts/generate_mailtrap_client.py generate inbound
    uv run python scripts/generate_mailtrap_client.py --target src/integrations/mailtrap

Requires the ``openapi-python-client`` dev dependency (already in ``[project.optional-dependencies]
dev``); run ``uv sync --extra dev`` if it is missing.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENDOR_DIR = REPO / "scripts" / "_vendor" / "mailtrap-openapi"
DEFAULT_TARGET = REPO / "src" / "integrations" / "mailtrap"

# Raw URLs on GitHub default branch. Pinned to a commit/tag? Not yet — bump ``SPEC_REF`` to a
# specific git ref (branch, tag, or sha) for reproducible generation.
SPEC_REF = "main"
RAW_BASE = f"https://raw.githubusercontent.com/mailtrap/mailtrap-openapi/{SPEC_REF}/specs"


@dataclass(frozen=True)
class Spec:
    key: str  # CLI selector + vendored filename stem
    filename: str  # vendored spec filename
    package: str  # generated python package name (also the on-disk dir name)
    project: str  # openapi-python-client project name (metadata only)
    summary: str

    @property
    def url(self) -> str:
        return f"{RAW_BASE}/{self.filename}"

    @property
    def vendored_path(self) -> Path:
        return VENDOR_DIR / self.filename

    def target_path(self, base: Path) -> Path:
        return base / self.package


SPECS: Sequence[Spec] = (
    Spec(
        key="inbound",
        filename="inbound.openapi.yml",
        package="mailtrap_inbound",
        project="mailtrap-inbound",
        summary="Inbound: folders, inboxes, received messages.",
    ),
    Spec(
        key="sending",
        filename="email-sending.openapi.yml",
        package="mailtrap_sending",
        project="mailtrap-sending",
        summary="Email Sending: domains, suppressions, stats, logs.",
    ),
    Spec(
        key="send",
        filename="email-sending-transactional.openapi.yml",
        package="mailtrap_send",
        project="mailtrap-send",
        summary="Transactional email sending (POST /api/send on send.api.mailtrap.io).",
    ),
)


def log(msg: str) -> None:
    print(f"[mailtrap-gen] {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(code)


def select_specs(names: Sequence[str]) -> list[Spec]:
    if not names:
        return list(SPECS)
    by_key = {s.key: s for s in SPECS}
    unknown = [n for n in names if n not in by_key]
    if unknown:
        die(f"unknown spec(s): {', '.join(unknown)}. known: {', '.join(by_key)}")
    return [by_key[n] for n in names]


def sync_specs(specs: Sequence[Spec]) -> None:
    """Download (refresh) the vendored OpenAPI spec files from GitHub."""
    import urllib.request

    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        log(f"sync {spec.key}: {spec.url}")
        with urllib.request.urlopen(spec.url) as resp:  # noqa: S310 — trusted https URL
            data = resp.read()
        spec.vendored_path.write_bytes(data)
        log(f"  wrote {spec.vendored_path.relative_to(REPO)} ({len(data)} bytes)")


def write_config(tmpdir: Path, spec: Spec) -> Path:
    """Emit a minimal openapi-python-client config pinning the package/project names."""
    # The CLI cannot override names per invocation, so we hand it a one-shot config file.
    cfg = tmpdir / "config.yaml"
    cfg.write_text(
        f"project_name_override: {spec.project}\npackage_name_override: {spec.package}\n",
        encoding="utf-8",
    )
    return cfg


def run_generator(spec: Spec, target: Path) -> None:
    """Run openapi-python-client for one spec and install the package at ``target``.

    Everything happens inside the temp dir context so the package is copied out before that dir
    is removed.
    """
    with tempfile.TemporaryDirectory(prefix=f"mt-{spec.key}-") as raw_cwd:
        cwd = Path(raw_cwd)
        cfg = write_config(cwd, spec)
        cmd = [
            sys.executable, "-m", "openapi_python_client",
            "generate",
            "--path", str(spec.vendored_path),
            "--config", str(cfg),
            "--meta", "none",
        ]
        log(f"generate {spec.key}: {' '.join(cmd[1:])}")
        result = subprocess.run(cmd, cwd=cwd, check=False)  # noqa: S603 — controlled argv
        if result.returncode != 0:
            die(f"openapi-python-client failed for {spec.key} (exit {result.returncode})")

        # With --meta none the package is written directly to cwd, named after ``package``.
        package_dir = cwd / spec.package
        if not (package_dir / "client.py").is_file():
            die(
                f"expected generated package at {package_dir}/client.py but it is missing; "
                f"contents of {cwd}: {sorted(p.name for p in cwd.iterdir())}"
            )
        install_package(package_dir, target)


_EXCLUDED_COPY_NAMES = {".ruff_cache", "__pycache__"}


def install_package(package_dir: Path, target: Path) -> None:
    """Copy a freshly generated package into place, dropping caches and stale files."""
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    def ignore(_dir: Path, names: list[str]) -> list[str]:
        return [n for n in names if n in _EXCLUDED_COPY_NAMES]

    shutil.copytree(package_dir, target, ignore=ignore)
    log(f"  installed -> {target.relative_to(REPO)}/")


def generate(specs: Sequence[Spec], target_base: Path) -> None:
    for spec in specs:
        if not spec.vendored_path.is_file():
            die(
                f"vendored spec missing: {spec.vendored_path.relative_to(REPO)}. "
                "Run with `sync` first (or no subcommand)."
            )
        run_generator(spec, spec.target_path(target_base))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=("all", "sync", "generate"),
        help="all = sync + generate (default); sync = refresh specs only; generate = regen from vendored specs",
    )
    parser.add_argument(
        "specs",
        nargs="*",
        metavar="SPEC",
        help=f"subset to act on (default: all). known: {', '.join(s.key for s in SPECS)}",
    )
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET, help="packages' parent dir")
    args = parser.parse_args(argv)

    specs = select_specs(args.specs)

    do_sync = args.command in ("all", "sync")
    do_generate = args.command in ("all", "generate")

    if do_sync:
        sync_specs(specs)
    if do_generate:
        generate(specs, args.target)

    log("done.")
    for spec in specs:
        if do_generate:
            print(f"{spec.key}\t{spec.target_path(args.target)}\t{spec.summary}")
        elif do_sync:
            print(f"{spec.key}\t{spec.vendored_path.relative_to(REPO)}\tsynced")


if __name__ == "__main__":
    main()
