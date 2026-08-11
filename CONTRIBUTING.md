# Contributing to Phulax

Thanks for your interest! Phulax is early-stage — the most valuable
contributions right now are bug reports, threat-model review, and small,
well-tested fixes.

## Getting set up

Requires [uv](https://docs.astral.sh/uv/) and Docker.

```bash
git clone https://github.com/phulax-io/phulax.git && cd phulax
cp .env.example .env      # fake values; fill in only what you need
make bootstrap            # venv + locked deps + pre-commit hooks
make test                 # must be green before and after your change
```

`make help` lists the full six-verb contract. If `make bootstrap && make test`
fails on a clean clone, that itself is a bug — please open an issue.

## Code style

- Formatting and linting are enforced by [ruff](https://docs.astral.sh/ruff/)
  via pre-commit — installed for you by `make bootstrap`. Don't hand-format.
- Python ≥ 3.12, type hints on public functions.
- Small files, small functions; match the style of the code around you.

## Before you build anything substantial

Read the three ADRs in [`docs/decisions/`](docs/decisions/) — they encode the
project's load-bearing bets (local gateway, metadata-first logging,
deterministic policy engine). A PR that cuts against an ADR needs an ADR of
its own, not just code. Open an issue to discuss first; it saves everyone
time.

Anything touching a protected action must satisfy the
[protected-action definition of done](docs/security/protected-action-dod.md):
authenticated, validated, policy-evaluated, idempotent, recorded, redacted,
tested.

## Submitting changes

1. Fork, create a branch from `main`.
2. Make the change, with tests. Bug fixes need a test that reproduces the bug.
3. Run `make test` — pre-commit hooks (format, lint, secret scan) run on commit.
4. Open a PR describing *what* and *why*. Small PRs merge fast; large
   unannounced ones stall.

Commit messages follow `<type>: <description>` (feat, fix, refactor, docs,
test, chore, perf, ci).

## Security issues

**Never open a public issue for a vulnerability.** See
[SECURITY.md](SECURITY.md) for private reporting.

## Secret hygiene

Never commit real credentials — `.env` is gitignored and `.env.example` must
contain only fake values. Gitleaks runs in pre-commit and CI; if it fires on
your PR, rotate the secret first, then fix the commit.

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), the same license as the project
(inbound = outbound).
