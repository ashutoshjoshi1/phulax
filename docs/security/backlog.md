# Security backlog

Seeded Day 0 from the 15 threats in the
[threat model](threat-model.md). One threat can spawn several items; every
item cites its threat ID. Re-groom at each phase boundary.

| # | Item | Threats | Phase |
|---|------|---------|-------|
| 1 | Default-deny per-agent tool/action allowlists in the policy engine | T4 | gateway v1 |
| 2 | Argument canonicalization before policy evaluation + bypass test table | T3 | gateway v1 |
| 3 | Idempotency keys + nonce checks for protected actions | T8 | gateway v1 |
| 4 | Authenticated event ingestion (gateway → control plane) | T10 | control plane v1 |
| 5 | Signed policy bundles; gateway rejects unsigned/stale policy | T10, T11 | control plane v1 |
| 6 | Fail-closed behavior for protected actions when control plane is unreachable | T12 | gateway v1 |
| 7 | Enforce metadata-only event schema; raw capture behind explicit per-tool flag + redaction | T13/R3 | gateway v1 |
| 8 | Tool registry as reviewed config (no dynamic tool discovery by default) | T6 | gateway v1 |
| 9 | Admin/policy changes recorded as decision events | T14 | control plane v1 |
| 10 | Approval UI shows rule + evidence; track approvals/hour per approver | T7 | dashboard v1 |
| 11 | Append-only event store; evaluate hash-chaining | T9 | control plane v2 |
| 12 | Result egress constraints (size/destination) in policy vocabulary | T5 | policy v2 |
| 13 | Deployment guide: locking down direct tool credentials so the gateway is the only path | T2 | pilot docs |
| 14 | Injection-resistance test suite: hostile prompts that attempt protected actions | T1 | demo phase |
| 15 | SBOM generation + artifact signing in CI | T15 | pre-GA |
| 16 | Separation of policy author / approver roles | T14 | control plane v2 |

Done on Day 0 (this scaffold): lockfiles (`uv.lock`), pre-commit secret
scanning (gitleaks), CI secret scan, Dependabot, `.env` hygiene — T15
foundations; metadata-first decided before any event exists — T13/R3.
