# Product Phase 0 — Day Zero: Workspace & Evidence System 🔜

**Plan source:** §6 (Day 0), §15.5 (decision log), §15.6 (README draft)
**Duration:** one focused day. Literally Day 0.

## Goal

Not a dashboard — an *environment where decisions, code, customer evidence,
security work, and operations can be trusted and repeated*. Done means:
private repo, reproducible local environment, written product boundary,
threat-model skeleton, interview list, decision log, and a seven-day calendar.
Test: **another developer could clone the repo and run a health check without
receiving secrets from you.**

## What you'll learn

- Why an *evidence system* precedes code (assumptions register, decision log)
- What ADRs are and why solo founders need them most
- Secret hygiene as a Day-0 habit, not a launch-week retrofit
- The Makefile as a contract with your future self

---

## Concepts

### Evidence beats memory

The plan demands: assumptions register (one row per belief that could kill the
company), an interview evidence log (§2.4 — one row per conversation, never
summarize ten interviews from memory), and a decision log (§15.5 — decision,
evidence, alternatives, review trigger). The discipline: **when you change
scope, record the evidence that justified it.** Six months from now, "why is
the gateway local?" has a written answer with the three prospect quotes that
forced it.

### ADRs — Architecture Decision Records

An ADR is a one-page file: *Context → Decision → Consequences → Evidence
needed to revisit.* You write three today (plan §6.4):

- **ADR-0001:** Local gateway + hosted control plane (the trust-boundary bet)
- **ADR-0002:** Metadata-first logging; raw content off by default
- **ADR-0003:** Deterministic policy engine before anomaly detection

Why ADRs matter more for a solo founder: you have no colleague whose memory
can check yours. ADRs are the colleague. Template is in plan §6.6.

### Secret hygiene from hour one

MFA on GitHub/cloud/email/registrar/password manager. `.env.example` with fake
values; real `.env` gitignored. Pre-commit secret scanning (e.g. gitleaks)
*before the first real secret exists* — retrofitting scanning after a leak is
incident response, not hygiene. Separate dev/prod cloud accounts even while
prod is empty: the boundary is cheap now, expensive later.

### The Makefile contract

```
make bootstrap   # venvs + locked dependencies
make dev         # postgres, redis, api, web, local gateway
make migrate     # apply schema
make seed        # demo org, agent, tools, policies
make test        # unit + integration
make demo        # one safe tool call through the gateway
```

Every phase from here on assumes these six verbs work from a clean clone.
"Works on my machine" is banned by construction.

---

## The work (plan §6.2–§6.5, condensed)

**Morning — founder & product**
1. One-page founder thesis: customer, painful workflow, promise, wedge, and
   what you *refuse* to build in 90 days.
2. Assumptions register started; customer list of 30, mark 10 for this week.
3. Define the first demo in one paragraph (refund agent, CRM, email, simulated
   payment, malicious ticket, approval, freeze, retest).

**Midday — engineering workspace**
4. Private `phulax` repo, protected main branch, MFA everywhere.
5. Toolchain: current Python, Node LTS, Docker. `.env.example` (plan §6.6
   gives the starter), `.gitignore` covering env/credentials/exports.
6. Makefile with the six verbs (stubs OK — `dev` may start only Postgres
   today). Lockfiles + dependency-update tooling + pre-commit
   (format/lint/secret-scan). CI that installs clean and runs one smoke test.

**Afternoon — documentation & security baseline**
7. `SECURITY.md` (reporting instructions + private contact).
8. ADR-0001/2/3. Data-flow diagram marking everywhere credentials, prompts,
   arguments, results can appear. Data inventory table (field, purpose,
   sensitivity, retention, access).
9. Security backlog seeded with the 15 threats (plan §4.3). Write the
   definition of done for a protected action: *authenticated, validated,
   policy-evaluated, idempotent, recorded, redacted, tested.*

**Evening — outreach & calendar**
10. Send five discovery messages (template: plan §13.2). Block two daily
    focus periods + Friday review. Write tomorrow's single outcome:
    *"An authenticated agent call reaches the gateway and produces a
    structured decision event."* Then stop.

### Verify

```bash
git clone <fresh clone> && cd phulax
make bootstrap && make test        # green from clean checkout
git log --oneline | head           # protected main, CI badge green
ls docs/decisions/                 # ADR-0001..0003 exist
```

## Exit criteria (plan §6.1)

- [ ] Repo + reproducible env; clean clone passes the smoke test
- [ ] Thesis, assumptions register, decision log, interview list exist
- [ ] Threat-model skeleton (15 threats) + data-flow diagram + data inventory
- [ ] 3 ADRs accepted; SECURITY.md present
- [ ] 5 outreach messages sent; 7-day calendar blocked

## Threats addressed

Foundational posture for **T15** (supply chain: lockfiles, scanning from day
one) and **R3** (accidental sensitive-data storage: metadata-first decided
*before* any event is ever written).

## Website tie-in

None yet — and that's the point: the site already says "early-stage" honestly.
Nothing on the site outruns reality today.

## Check your understanding

1. Why does the plan insist Day 0 is *not* "build the dashboard"?
2. What are the four sections of an ADR, and which one forces intellectual
   honesty about the future?
3. Why create separate dev/prod cloud accounts when prod is empty?
4. What is the Day 0 "another developer could…" test actually testing?

## Kick off with Claude Code

> "Scaffold the phulax monorepo per build plan §5.3 and §6: Makefile with the
> six verbs, docker-compose (postgres+redis), .env.example, pre-commit with
> secret scanning, CI smoke test, SECURITY.md, and ADR-0001..0003 drafts."
