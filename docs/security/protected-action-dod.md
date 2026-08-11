# Definition of done: a protected action

A tool call classified as *protected* (money moves, data leaves, state is
destroyed, access is granted) is **done** only when all seven hold. This
checklist gates every gateway feature from Day 1 onward; a protected action
missing any line is a bug, not a backlog item.

1. **Authenticated** — the calling agent's identity is verified; anonymous
   calls to protected actions are impossible by construction.
2. **Validated** — arguments are canonicalized and schema-checked *before*
   policy evaluation; malformed input is rejected, not guessed at (T3).
3. **Policy-evaluated** — a deterministic verdict exists citing the exact
   rule and policy version that produced it (ADR-0003). No code path
   executes a protected action without a verdict.
4. **Idempotent** — replaying the same request (or its approval) cannot
   execute the action twice (T8).
5. **Recorded** — a decision event exists before the action's effects do;
   if the event cannot be written, the action does not proceed.
6. **Redacted** — the recorded event is metadata-first; raw content appears
   only under an explicit opt-in with redaction applied (ADR-0002, T13).
7. **Tested** — allow, block, require-approval, replay, and malformed-input
   paths each have a test; the bypass table for its rule types passes.
