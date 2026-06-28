# Skill Security Crossdoc Live Results

The 2026-06-27 skill-security cross-document live run is a valid controlled execution artifact, but not a full answer-quality pass.

## Gate Summary

Execution gate: passed.

- 5/5 test questions returned responses.
- All question requests returned HTTP 200.
- API log evidence records five `POST /chat HTTP/1.1` requests returning `200 OK` in `artifacts/skill-security-crossdoc-testset/2026-06-27/api.out.log`.
- Every response used the three-paper scope.
- Uploaded page counts matched the expected corpus: Skill-Inject 18/18, Wild Skills 20/20, Trojan Whisper 17/17.
- The redacted run artifact parsed successfully and recorded no structural validation failures.

Answer quality gate: partial.

- Automatic scorecard mean: 7.6/10.
- Manual quality-review mean: 5.3/10.
- Main reason for the difference: the automatic scorecard over-rewards structural source coverage and answer formatting, while manual review penalizes missing numeric anchors, low-confidence evidence, insufficient-evidence traces, and report-facing overclaims.

## Manual Quality Findings

| Question | Manual score | Report use |
| --- | ---: | --- |
| Q1 Attack Surface Comparison | 6.5/10 | Cautious qualitative support only |
| Q2 Evidence That The Threat Is Commercially Real | 3.5/10 | Failure-boundary example, not a success case |
| Q3 Mixed Skill Risk Classification | 5.5/10 | Provisional taxonomy synthesis |
| Q4 Are Simple Defenses Enough? | 6.5/10 | Directionally useful after adding missing anchors |
| Q5 Defense Story For The PaperMemory Report | 4.5/10 | Overclaim-risk example, not report-ready |

Q2 is the clearest grounding failure. The answer did not recover the expected cross-paper numeric evidence and explicitly reported missing evidence for major parts of the question. This should not be described as a successful numerical-grounding case.

Q5 is the clearest claim-boundary failure. The answer moves from evidence synthesis into an unsupported defense workflow and risks implying a broader security capability than the live test demonstrates.

## Report-Facing Conclusion

This run can support a controlled evaluation story for agentic autonomy, trust, and robustness: PaperMemory can be tested on a realistic multi-paper security corpus, can retrieve and synthesize some cross-document evidence, and can expose failure boundaries through insufficient-evidence and low-confidence evidence signals.

The run cannot support broad claims that PaperMemory detects all malicious skills, performs general malware detection, guarantees security QA, or enables autonomous safe execution in arbitrary repositories. Retrieved security-paper content should be treated as evidence for analysis, not as operational instruction.

Best report wording: "The skill-security live test passed structural execution gates and produced useful evidence of controlled cross-document evaluation, but manual review found only partial answer quality. The strongest result is not a blanket security capability claim; it is a bounded demonstration of evidence gathering, synthesis attempts, and visible failure modes under human review."
