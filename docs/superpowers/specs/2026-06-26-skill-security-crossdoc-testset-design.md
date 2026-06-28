# Skill Security Cross-Document Testset Design

## Goal

Create a compact five-question evaluation set from three agent-skill security papers to test PaperMemory's real report/demo story: agentic retrieval, cross-document synthesis, grounded reasoning, and safe handling of malicious-instruction content.

## Source Papers

- `skill inject.pdf`: Skill-Inject benchmark for skill-file prompt injection, 18 pages.
- `malicous agent skill.pdf`: large-scale empirical study of malicious agent skills in the wild, 20 pages.
- `trojan whisper.pdf`: Trojan's Whisper study of OpenClaw guidance injection, 17 pages.

## Design Principles

- Keep the set small enough for a live demo: exactly five questions.
- Require at least two documents for most answers, and all three documents for synthesis questions.
- Make expected answers evidence-checkable with page anchors and numeric facts.
- Include one safety-oriented question where retrieved attack descriptions must be treated as evidence, not instructions.
- Avoid operational exploit instructions; describe risks and defenses at a high level.

## Capability Coverage

| Capability | Covered By |
| --- | --- |
| Cross-document retrieval | Questions 1, 2, 4, and 5 require evidence from all three papers. |
| Numerical grounding | Question 2 checks exact benchmark/ecosystem/evaluation numbers. |
| Reasoning over taxonomy | Question 3 asks the agent to classify a mixed hypothetical using paper taxonomies. |
| Trust and robustness | Question 4 tests whether the agent rejects weak defenses such as simple filtering alone. |
| Report/demo usefulness | Question 5 turns paper findings into a commercial-grade defense story. |

## Execution Shape

The future test run should upload the three PDFs into a clean PaperMemory group, ask each question once with hybrid retrieval and agentic retrieval enabled, then record:

- evidence packet source documents and pages;
- answer claims and numeric facts;
- agent trace stop reason;
- whether the answer follows any instruction-like text from retrieved evidence;
- a per-question score using the rubric in `reports/final/results/skill_security_crossdoc_testset.md`.

## Scope Boundary

This is a controlled report/demo test set, not a broad security benchmark. It supports claims that PaperMemory can retrieve and synthesize evidence across a small corpus of related papers. It should not be presented as measuring general security-research QA performance.
