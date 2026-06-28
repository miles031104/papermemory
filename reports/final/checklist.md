# NeurIPS-style Checklist Answers

This is the human-readable checklist companion for `main.tex`. It follows the NeurIPS checklist style, but the report is a course deliverable rather than a formal NeurIPS submission.

| Item | Answer | Support |
| --- | --- | --- |
| Claims reflect contributions and scope | Yes | Abstract, Introduction, Limitations, and `claim_evidence_map.md` separate technical results, early market evidence, and commercial estimates. |
| Limitations are discussed | Yes | Section `Limitations, Ethics, and Reproducibility` and appendices cover synthetic fixtures, controlled live tests, no OCR robustness, no dense semantic retrieval, no broad user study, and licensing risk. |
| Theory assumptions and proofs | Not applicable | The paper does not introduce theorems or formal proofs. |
| Reproducibility | Yes | Appendix A, `build_notes.md`, Node 0 environment artifacts, and the keyword-baseline command record repository root, branch, toolchain, commands, and artifact paths. |
| Dataset and evidence details | Yes | The report describes the synthetic fixture suite, controlled live test, keyword baseline, and aggregate-only 10-person postgraduate interview protocol. |
| Compute resources | Yes | Local Python/Node/npm versions, local API/UI test context, and LaTeX compile command are recorded. |
| Ethics and broader impacts | Yes | The report emphasizes human verification, local-first/BYOK boundaries, external API risk, prompt-boundary limits, and licensing risk. |
| Safeguards | Yes | Robustness matrix covers empty scope, missing evidence, no-new-evidence, prompt-injection-like text, citation drift, conflicting numeric evidence, low-text markers, and reliability status. |
| Market proof | Yes, bounded | Interview evidence provides early conditional purchase intent and API/subscription preference, not actual conversion or retention. |
| Commercial stress test | Yes | Cost model records token/API cost, labor assumptions, verification time, weekly capped managed-LLM tier assumptions, and sensitivity ranges. |
| Road-show alignment | Yes | A separate three-minute demo video accompanies the submission; the PDF keeps the road-show outside the appendix and focuses on reproducibility and claim-boundary notes. |
| Licenses and assets | Yes | PyMuPDF/MuPDF AGPL/commercial-license exposure is documented as a deployment risk. |

Residual checklist concerns:

- Evaluation is intentionally synthetic/local and should not be presented as broad external performance evidence.
- Interview evidence is a small convenience sample and should not be presented as product-market fit.
- Cost model sources are a 2026-06-24 snapshot, and weekly tier caps are planning assumptions that should be refreshed before external use.
- A separate three-minute demo video accompanies the submission; the PDF does not duplicate the video storyboard or map road-show scenes in an appendix.
- Commercial deployment needs licensing review for PyMuPDF/MuPDF.
