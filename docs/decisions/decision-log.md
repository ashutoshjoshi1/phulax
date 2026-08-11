# Decision log

One row per decision that shapes the product (plan §15.5). When scope
changes, record the evidence that justified it — six months from now,
"why is the gateway local?" must have a written answer.

| Date | Decision | Evidence | Alternatives considered | Review trigger |
|------|----------|----------|------------------------|----------------|
| 2026-08-11 | Local gateway + hosted control plane ([ADR-0001](ADR-0001-local-gateway-hosted-control-plane.md)) | Security buyers won't route credentials through third-party cloud; latency tax on every tool call | Fully hosted proxy; purely local binary with no control plane | ≥3 design partners blocked by self-hosting burden |
| 2026-08-11 | Metadata-first logging, raw content off by default ([ADR-0002](ADR-0002-metadata-first-logging.md)) | Raw prompts/args contain PII & secrets; storage = breach liability (R3); must be decided before first event is written | Full capture with redaction; full capture, encrypted | Partners repeatedly unable to resolve incidents with metadata alone |
| 2026-08-11 | Deterministic policy engine first; anomaly detection later, advisory-only ([ADR-0003](ADR-0003-deterministic-policy-engine-first.md)) | Buyers demand predictable enforcement; no behavior corpus exists to train on | ML anomaly detection as enforcement; hybrid from day one | Event corpus large enough for honest evaluation; partners hit rule-fatigue |
| 2026-08-11 | Product is open source; public repo at phulax-io/phulax | Founder decision (2026-08-11): OSS gateway lowers the trust barrier ADR-0001 identifies; pricing page removed from site | Closed source; open-core split decided later | Monetization design forces an explicit open-core boundary |
| 2026-08-11 | Monorepo; Python managed by uv with locked deps; six-verb Makefile as the reproducibility contract | Solo founder: one repo, one lockfile, one CI; clean-clone test in plan §6 | Polyrepo per service; poetry/pip-tools | Team growth or a component (web) needing an independent release cadence |
| 2026-08-11 | Walking-skeleton stack: FastAPI + SQLAlchemy 2 + Alembic on Postgres; HS256 dev tokens (shared signing key) until workload identity lands | Thinnest slice through every layer beats best-of-breed per layer (plan §7); HS256 is honest for dev-only issuance | Django (heavier), asyncpg direct (no migration story), RS256 + JWKS now (premature) | Multi-gateway deployments or key-rotation need force asymmetric signing; revisit at control plane v1 |
| 2026-08-11 | OSS license: **Apache-2.0** | Founder asked for a license Day 0; Apache-2.0 is the enterprise-friendly default for security infra (patent grant, permissive) | MIT (no patent grant), AGPL-3.0 (deters enterprise adoption), BSL (not OSI-open) | Monetization design forces an open-core boundary, or a relicensing question arises before external contributions accumulate |
