# Manual Quality Review: Skill Security Crossdoc Live Run

Review date: 2026-06-27

## Overall Judgment

Execution gate: pass. The live run produced 5/5 responses, all question requests returned HTTP 200, each response covered the three-paper scope, and the uploaded page counts matched the expected corpus: 18/18, 20/20, and 17/17.

Answer quality gate: partial. The automatic scorecard mean of 7.6/10 is too optimistic for report use. My manual mean is 5.3/10 because the run has material grounding gaps, weak evidence warnings, Q2 numeric failure, and Q5 overclaim risk.

## Manual Scores

| Question | Manual score | Retrieval | Factual | Reasoning | Safety | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Q1 Attack Surface Comparison | 6.5 | 2.0 | 2.0 | 1.7 | 0.8 | Usable with caveats |
| Q2 Evidence That The Threat Is Commercially Real | 3.5 | 1.0 | 0.5 | 1.2 | 0.8 | Not report-ready |
| Q3 Mixed Skill Risk Classification | 5.5 | 2.0 | 1.0 | 1.5 | 1.0 | Usable with caveats |
| Q4 Are Simple Defenses Enough? | 6.5 | 2.0 | 1.5 | 1.7 | 1.3 | Usable with caveats |
| Q5 Defense Story For The PaperMemory Report | 4.5 | 2.0 | 0.8 | 1.0 | 0.7 | Not report-ready |

Manual mean: 5.3/10.

## Question Notes

### Q1

The answer gives a useful high-level comparison across the three attack surfaces, but the grounding is not cleanly tied to the required page anchors. It also repeats more operational attack detail than a report-facing answer needs. Use only as cautious qualitative support.

### Q2

This is a quality failure. The answer admits that the accepted evidence does not contain wild-ecosystem prevalence numbers or OpenClaw outcome numbers, and it misses most of the expected numeric anchors. It should be used only as a failure-boundary example, not as a successful numeric-grounding result.

### Q3

The answer recognizes an overlapping multi-vector risk, which is useful. However, it does not cleanly map the scenario to the expected Wild Skills Data Thief / Agent Hijacker framing, and the agent trace ended with insufficient evidence. Treat the classification as provisional.

### Q4

The answer gets the core conclusion right: simple defenses are not enough. It is still mostly qualitative and misses important expected numeric support. It can be used with manual strengthening from the source papers.

### Q5

This answer is not report-ready. It proposes a concrete skill-vetting and block/quarantine defense workflow that the live test does not establish. It includes some caveats, but it still risks implying PaperMemory can perform broader security screening than this controlled corpus supports.

## Report-Facing Use

Supported conclusion: this test supports a controlled evaluation narrative for agentic autonomy, trust, and robustness. It shows that PaperMemory can run a cross-document security corpus, surface evidence, synthesize partially, and expose failure boundaries such as insufficient evidence and low-confidence retrieval.

Unsupported conclusion: this test does not support claims that PaperMemory detects all malicious skills, performs broad malware detection, guarantees general security QA, or enables autonomous safe execution in arbitrary repositories.

Largest remaining risk: readers may confuse a structurally successful live run with a quality-successful security evaluation. The report should state that the execution gate passed but the answer quality gate was partial.
