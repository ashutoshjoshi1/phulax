# ADR-0003: Deterministic policy engine before anomaly detection

**Status:** accepted
**Date:** 2026-08-11

## Context

Two credible designs exist for deciding whether an agent's tool call is
allowed: deterministic rules (allowlists, parameter constraints, rate and
amount limits, approval triggers) or learned anomaly detection. Anomaly
detection demos well but cannot explain its verdicts, needs a corpus of
agent behavior we do not have, and fails the question every security buyer
asks first: "what exactly will this block?" A gateway that blocks
unpredictably will be bypassed or uninstalled within a week.

## Decision

Version 1 of the policy engine is fully deterministic: the same call under
the same policy always produces the same verdict, and every verdict cites
the rule that produced it. Policies are data (reviewable, diffable,
testable), and the engine is table-driven-testable. Anomaly detection, if it
comes, arrives later as an *advisory* signal layered on top — never as the
enforcement path — and only once the decision-event corpus is large enough
to train and evaluate it honestly.

## Consequences

Easier: explaining any verdict to a customer; writing tests (input → verdict
tables); auditing ("show me why this was blocked" has an exact answer);
building trust with security teams.

Harder: novel attacks that fit no written rule pass through — coverage is
only as good as the policy author. Rule sets can grow unwieldy without good
defaults and templates.

Given up: "AI-powered detection" as a launch differentiator.

## Evidence needed to revisit

- Decision-event corpus reaches a size where behavioral baselines are
  statistically meaningful per-agent.
- Design partners report real incidents that deterministic rules missed and
  an advisory scorer would plausibly have flagged.
- Rule fatigue: customers' policy sets grow past what they can maintain,
  and they ask for adaptive help.
