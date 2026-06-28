# Evidence Reliability Layer

PaperMemory exposes answer grounding as a visible reliability status instead of hiding uncertainty inside generated prose. The layer is domain-neutral: it plans evidence requirements from the question, checks paper and claim-type coverage, verifies answer claims against accepted evidence, and returns `strong`, `partial`, or `insufficient` status with visible limits.

## Supported Boundary

Supported: PaperMemory can show whether an answer is strongly, partially, or insufficiently grounded in the selected evidence by combining requirement planning, coverage checks, claim verification, and user-visible limits.

Unsupported: this does not prove exhaustive literature-review coverage, universal malicious-skill detection, or autonomous safe execution.

## Report And Demo Use

- Agentic autonomy: the system can plan evidence needs, request targeted coverage, and surface when a response should be withheld or reviewed.
- Trust and robustness: reliability status gives reviewers a concrete boundary for accepting, revising, or rejecting an answer.
- Commercial stress test and cost: disabled reliability mode avoids extra planner checks, while enabled status supports human review when stronger grounding matters.

The artifact should be used as claim-bounded support for the final report and demo, not as a performance result. No unverified accuracy, latency, or cost numbers are claimed here.
