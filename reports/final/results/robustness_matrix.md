# Node 8 Robustness Matrix

Node 8 adds deterministic regression evidence for PaperMemory trust behavior. It does not claim comprehensive security, OCR robustness, adversarial benchmark coverage, or real-corpus reliability.

| Case | Expected behavior | Test evidence | Claim boundary |
| --- | --- | --- | --- |
| Empty scope | No selected or ready papers produces conversation-mode limits and strips paper-style citations from the generated answer. | `test_empty_scope_strips_paper_citations_and_marks_conversation_mode_limit` | Deterministic no-scope citation containment, not proof that all unsupported prose is detected. |
| Missing evidence | Scoped retrieval with no accepted units returns `partial`, carries no accepted citations, and strips scoped citation drift. | `test_missing_scoped_evidence_is_partial_limited_and_cites_nothing` | Covers empty accepted packets for known paper scope. |
| No-new-evidence loop | A second retrieval pass that repeats the same accepted page stops with `no_new_evidence` in the public trace. | `test_no_new_evidence_second_pass_stops_with_trace_reason` | Covers page-deduped evidence delta, not semantic novelty. |
| Prompt-injection PDF text | Injection-like captions appear only inside the accepted evidence section, while planner prompts state PDF text is untrusted evidence. | `test_planner_prompt_labels_prompt_injection_pdf_text_as_untrusted_evidence` | Prompt-boundary regression, not a complete prompt-injection proof. |
| Prompt-injection planner hints | Extra tool/action fields stop safely; unsafe query or missing-evidence hints are removed from retrieval and public trace text, including unsupported retrieval-mode planner paths. | `test_planner_extra_tool_action_from_pdf_injection_stops_safely`, `test_public_trace_redacts_prompt_injection_planner_queries_and_missing_evidence`, `test_unsupported_planner_mode_redacts_missing_evidence_hints` | Pattern-based deterministic redaction for known unsafe phrases. |
| Citation drift | Generated citations outside accepted packet pages are stripped before response serialization, including unknown-paper labels. | `test_citation_drift_outside_accepted_packet_is_stripped`, `test_citation_drift_unknown_paper_id_is_stripped` | Page-label containment for simple `paper_id p.N` citations. |
| Conflicting evidence | Accepted pages with conflicting numeric values add a verification-needed packet limit and expose that limit in the final prompt preview. | `test_conflicting_evidence_adds_uncertainty_limit` | Simple numeric-conflict heuristic for reportable deterministic fixtures. |
| Low-text/scanned marker | Evidence units marked low-text, empty, or OCR-needed add a visual-first limit and warn against inventing missing text. | `test_low_text_or_scanned_marker_adds_visual_first_limit` | Uses manifest/packet quality markers; OCR is not implemented. |

Latest focused verification before controller review:

```text
python -m pytest apps/api/tests/test_prompt_injection_pdf.py apps/api/tests/test_retrieval_robustness.py -q
11 passed
```
