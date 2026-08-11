# Assumptions register

One row per belief that could kill the company (plan §2.4). Every scope
decision should trace to a row here. Statuses: `untested`,
`testing`, `supported`, `weakened`, `killed`.

| ID | Assumption | How we test it | Evidence so far | Status | Kill criteria |
|----|-----------|----------------|-----------------|--------|---------------|
| A1 | Teams deploying tool-using agents fear agent-initiated actions enough to install a gateway in front of them | 10 discovery interviews this week; count unprompted mentions of the fear | — | untested | <3 of 10 interviewees describe the pain unprompted |
| A2 | Security buyers require enforcement to run in their own environment (credentials never leave) | Ask directly in interviews; offer hosted-proxy strawman and record reactions | — | untested | Majority would accept a hosted proxy from a startup |
| A3 | A deterministic, explainable policy engine is enough for a valuable v1 (no ML needed) | Demo policy engine to design partners; count "but does it detect X automatically?" objections that block adoption | — | untested | Partners consistently refuse pilot without behavioral detection |
| A4 | One engineer can adopt the OSS gateway in an afternoon without procurement | Time-to-first-decision-event measured with pilot users | — | untested | Median setup time exceeds a day, or procurement is triggered anyway |
| A5 | The approval workflow (human-in-the-loop for dangerous actions) fits how these teams already work | Interviews: who would approve, and would they tolerate the interruption? | — | untested | Approvals routinely bypassed or auto-accepted within a week |
| A6 | Companies will pay for the hosted control plane even with a free OSS gateway | Pricing conversations after pilot value is shown | — | untested | Pilots run indefinitely on OSS-only with no upgrade pressure |

**Discipline:** update the *Evidence so far* column after every interview or
pilot session — link the interview-log row, never paraphrase from memory.
