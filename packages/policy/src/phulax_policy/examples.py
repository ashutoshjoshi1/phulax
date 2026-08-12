"""The canonical example bundle (plan §7.2) — the same one on the website.

Four canonical rules plus ``allow-small-refund``, which makes the refund
path executable so idempotency (Day 13) has a side effect to protect.
Used by the seed script, the docs, and the test suite alike.
"""

CANONICAL_BUNDLE_YAML = """\
rules:
  - id: allow-read-order
    effect: allow
    match:
      tool: read_order

  - id: allow-small-refund
    effect: allow
    match:
      tool: issue_refund
    conditions:
      - field: arguments.amount
        op: lte
        value: 50

  - id: approve-large-refund
    effect: require_approval
    match:
      tool: issue_refund
    conditions:
      - field: arguments.amount
        op: gt
        value: 50
    approver_role: finance_approver

  - id: block-external-sensitive-email
    effect: deny
    match:
      tool: send_email
    conditions:
      - field: arguments.to
        op: not_ends_with
        value: "@demo-org.dev"

  - id: freeze-on-revoked-agent
    effect: freeze
    match: {}
    conditions:
      - field: agent.revoked
        op: eq
        value: true
"""
