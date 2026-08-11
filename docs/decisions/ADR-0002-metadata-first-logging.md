# ADR-0002: Metadata-first logging; raw content off by default

**Status:** accepted
**Date:** 2026-08-11

## Context

Every agent tool call that passes through the gateway could be recorded in
full: prompt, arguments, results. Full capture is tempting — it makes
debugging and forensics trivial — but prompts and arguments routinely contain
PII, secrets, and customer data. Storing them by default turns our audit
trail into a data-breach liability, drags every sales conversation into data-
processing review, and contradicts the trust-boundary bet of ADR-0001. This
risk (accidental sensitive-data storage, risk R3 in the threat model) must be
decided *before* the first event is ever written, because retrofitting
redaction onto an existing raw-content store is incident response, not
design.

## Decision

Decision events record metadata by default: agent identity, tool and action
names, argument hashes, types and sizes, the policy verdict and the rule that
produced it, approver identity, timestamps, and latency. Raw content capture
is off by default and can only be enabled as an explicit, per-tool,
per-deployment opt-in with redaction applied before storage.

## Consequences

Easier: security review and procurement ("we don't store your data" is
verifiable from the schema); compliance posture; keeping the control plane a
low-value target.

Harder: debugging policy mismatches and investigating incidents without
payloads — metadata design must be good enough that hashes, types, and sizes
answer most questions. Support will sometimes need customers to reproduce
issues locally.

Given up: effortless forensics and replay from our own store.

## Evidence needed to revisit

- Design partners repeatedly cannot resolve real incidents with metadata
  alone and ask for payload capture despite the liability.
- Redaction/tokenization reaches the point where raw capture no longer
  stores sensitive values in practice.
- A regulated buyer *requires* full-content audit trails as a condition of
  purchase, and that segment matters.
