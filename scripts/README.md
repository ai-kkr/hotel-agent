# scripts/

Dev-only utilities for the kkr-hotel-assist project. **Not imported by production code**
(`src/`). This package is a sibling of `src/` and lives outside the shipped application.

## booking-corpus-collector

Collects a diverse corpus of **forwarded hotel-booking confirmations** from your personal Gmail
and writes them as replay-ready `.eml` files so you can manually drive the full `booking-intake`
chain (authentication, routing, forward/cover separation, extraction).

### Why forward-wrapped (layer A+B)

`booking-intake` expects a client *forward* to `c.<token>@kkr-hotel.com` and separates the
client's cover note (wishes) from the forwarded booking. This tool rebuilds each fetched
confirmation as such a forward, so the whole chain gets exercised — not just the extractor.

## One-time Gmail setup (OAuth, no 2FA required)

1. Google Cloud Console → create (or pick) a project.
2. Enable the **Gmail API**.
3. **OAuth consent screen** → External → add yourself as a Test User.
4. **Credentials** → Create credentials → **OAuth client ID** → Application type **Desktop app**
   → download the JSON.
5. Save the downloaded JSON as `credentials.json` in your working directory (it is gitignored).

> Because the app stays in **Testing** status, Google shows an "unverified app" warning on first
> login — click *Advanced → Go to … (unsafe)*. That is expected for a personal dev tool.

## First run (browser consent) and later runs

```bash
uv run python -m scripts.collect_corpus \
    --client-email you@example.com \
    --recipient c.demo@kkr-hotel.com
```

- **First run** opens a browser; log in with your normal Google password (no 2FA needed),
  approve access. `ezgmail` stores a refresh token in `token.json` (gitignored).
- **Later runs** reuse the token — no browser.

> **Port note:** `oauth2client`'s OAuth callback defaults to port **8080**, which this project's
> `docker-compose.yml` maps to the `temporal-ui` container — Docker/OrbStack intercepts it, so the
> post-consent redirect lands on the Temporal dashboard instead of writing `token.json`. The tool
> pins the callback to **8411** by default; override with `--auth-port` / `KKR_GMAIL_AUTH_PORT`.
> If you've stopped the Docker stack, 8080 is free and any port works.

Output goes to `~/.kkr-hotel-corpus/` by default (`--out-dir` to change): `booking-001.eml` …
`booking-NNN.eml` plus `manifest.json` (system, sender, subject, date, confidence, cover note).

## Options

| Flag | Default (env) | Meaning |
|---|---|---|
| `--count` | `10` (`KKR_CORPUS_COUNT`) | How many diverse confirmations to keep |
| `--query` | wide booking query (`KKR_CORPUS_QUERY`) | Gmail UI search operators |
| `--client-email` | — (`KKR_CLIENT_EMAIL`) | Your registered client address (the forward `From:`) |
| `--recipient` | `c.demo@kkr-hotel.com` (`KKR_CORPUS_RECIPIENT`) | The `c.<token>@<mail-domain>` target |
| `--out-dir` | `~/.kkr-hotel-corpus` (`KKR_CORPUS_OUT`) | Output directory (outside the repo by default) |
| `--confidence-threshold` | `0.6` (`KKR_CONFIDENCE`) | Min classifier confidence to keep |
| `--wishes` | `mixed` (`KKR_CORPUS_WISHES`) | `none` or `mixed` cover-note wishes |
| `--credentials` / `--token` | `credentials.json` / `token.json` | OAuth paths |

## Privacy

These emails contain your personal data (name, travel dates, hotel address, confirmation
number). **They must never enter the repository.** The default output dir is outside the repo,
and `*.eml`, `credentials.json`, `token.json`, and `corpus_output/` are gitignored. The tool
does **not** anonymize — it is for your personal testing only.
