# The first demo, in one paragraph

A refund agent handles support tickets with real tool access — CRM lookups,
email, and a *simulated* payment API — all through the Phulax gateway. A
normal ticket flows end-to-end: the agent reads the ticket, checks the
order, issues a small refund, and every step lands in the decision log as a
metadata-first event. Then a malicious ticket arrives (a prompt-injection
attempt pushing an oversized refund to a new payee): the gateway's policy
holds the action, a human sees exactly which rule fired and why, denies it,
and freezes the agent with one action. After the operator retests with the
freeze lifted and a corrected policy, the same attack is blocked outright —
demonstrating detection, human control, kill-switch, and auditability in
under five minutes, without Phulax ever storing the ticket's contents.

Everything in this paragraph is the acceptance test for the demo phase; if a
sentence here can't be shown live, the phase isn't done.
