# Founder thesis (one page)

> **Status: DRAFT — founder to edit in their own words.** This page is the
> product's spine; every scope decision should be checkable against it.

## Customer

The engineering or platform-security lead at a company that has moved AI
agents past chat and into *actions* — agents that touch the CRM, send email,
issue refunds, modify infrastructure. Small enough that this person is also
the one who gets paged; large enough that an agent mistake has a blast
radius.

## Painful workflow

They shipped an agent that can act, and now every capability grant is a
negotiation with their own fear. Today's options are all bad: hand the agent
raw API keys and hope; wrap every tool in bespoke if-statements that nobody
audits; or stall the rollout. When something odd happens, the "audit trail"
is a grep through LLM logs full of customer data.

## Promise

Every consequential thing your agents do passes through one gate you
control: a deterministic policy decides it, a human approves the dangerous
ones, a metadata-first event records it, and one switch freezes everything.
Your credentials and your data never leave your environment.

## Wedge

The open-source local gateway. It's adoptable by one engineer in one
afternoon without a procurement conversation, and it earns the trust that a
hosted-everything security product can't. The hosted control plane
(approvals, policy authoring, audit views for the team) is the natural next
step once the gateway proves itself.

## What we refuse to build in the next 90 days

- Anomaly detection or any ML-based enforcement (ADR-0003)
- Raw-content logging pipelines (ADR-0002)
- A hosted proxy that terminates customer tool traffic (ADR-0001)
- Agent *frameworks*, orchestration, or prompt tooling — we govern actions,
  we don't author them
- Compliance reporting suites (SOC2 dashboards etc.) before there are
  events worth reporting on
