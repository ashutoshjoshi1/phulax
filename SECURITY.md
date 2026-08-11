# Security Policy

Phulax is a security product; reports about Phulax itself are treated as
priority zero.

## Reporting a vulnerability

**Please do not open a public issue for security reports.**

- Email: **security@phulax.io** (monitored by the founder)
- Alternatively, use GitHub's private vulnerability reporting on this
  repository ("Report a vulnerability" under the Security tab).

Include what you can: affected component (gateway, control plane API, web),
reproduction steps, impact, and any suggested fix. Proof-of-concept code is
welcome; please don't test against infrastructure you don't own.

## What to expect

- Acknowledgment within **48 hours**.
- An assessment and remediation plan within **7 days**.
- Credit in the release notes if you'd like it (or anonymity if you prefer).

This is an early-stage project without a bug bounty yet; good-faith research
under coordinated disclosure will never result in legal action from us.

## Scope notes

- The gateway runs in *your* environment by design ([ADR-0001](docs/decisions/ADR-0001-local-gateway-hosted-control-plane.md));
  misconfigurations of your deployment are out of scope, but unclear docs
  that *caused* the misconfiguration are in scope — report those too.
- The decision-event pipeline is metadata-first ([ADR-0002](docs/decisions/ADR-0002-metadata-first-logging.md));
  any path that leaks raw prompts, arguments, results, or credentials into
  the control plane is a vulnerability, not a feature request.
