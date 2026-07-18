# Caddy proxy for temporal-ui (basic auth + reverse proxy).
# Uses the official image's default ENTRYPOINT/CMD, which runs
# `caddy run --config /etc/caddy/Caddyfile --adapter caddyfile` — we just bake our Caddyfile
# into that exact path, so no start-command / entrypoint wrangling is needed.
FROM caddy:2.8-alpine

COPY Caddyfile /etc/caddy/Caddyfile
