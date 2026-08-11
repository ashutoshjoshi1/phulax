# ADR-0001: Local gateway, hosted control plane

**Status:** accepted
**Date:** 2026-08-11

## Context

Phulax intercepts the most sensitive traffic a company has: the tool calls
its AI agents make, including the credentials that authorize them and the
arguments and results that flow through them. Security buyers will not route
that traffic through a third-party cloud proxy — doing so would make Phulax
itself the largest new attack surface in their environment, and would add a
network round-trip to every tool call. At the same time, policy management,
human approvals, and audit review need a place a team can log into, which a
purely local binary cannot provide.

## Decision

The enforcement point (the gateway) runs inside the customer environment.
The control plane is hosted by us and handles policy authoring, approval
workflows, and decision-event review. Policies flow down to the gateway;
decision-event *metadata* flows up (see ADR-0002). Tool credentials, raw
prompts, arguments, and results never leave the customer environment.

## Consequences

Easier: the trust conversation with security teams ("your credentials never
leave your network" is a one-sentence answer); procurement and security
review; no latency tax on tool calls; a clean story for the open-source
gateway.

Harder: we ship and support software running on machines we don't control —
version skew, upgrade paths, and debugging without access all become our
problem. The gateway must degrade safely when the control plane is
unreachable (cached policies, fail-closed for protected actions).

Given up: the operational simplicity of a single hosted proxy, and the
ability to hotfix enforcement logic server-side.

## Evidence needed to revisit

- Three or more design partners independently ask for a fully hosted proxy
  because operating the local gateway blocks their adoption.
- Gateway operational burden (upgrade failures, support load) measurably
  stalls pilots.
- A deployment model emerges (e.g. customer-cloud managed instances) that
  preserves the credential boundary without self-hosting.
