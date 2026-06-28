# Claim-Evidence Map

This map covers the major Abstract and Introduction claims after the course-report rewrite. Claims marked `supported` are supported within the stated local, controlled, or early-market boundary.

## PDF-Visible Summary Table

The report now includes `reports/final/tables/claim_evidence_boundary.tex`, a compact in-PDF table with five major claims: market signal, compound AI architecture, synthetic retrieval results, bounded subscription cost logic, and trust behavior. The table now keeps only the claim and evidence columns so the main PDF stays readable.

| Claim | Status | Evidence |
| --- | --- | --- |
| PaperMemory targets a paid postgraduate PDF evidence workflow. | Supported as early market signal | `reports/final/results/interview_market_validation.md`; `reports/final/tables/market_validation.tex`. |
| Ten postgraduate interviewees reported mean conditional purchase likelihood of 4.2/5 if PaperMemory delivers the claimed workflow. | Supported as convenience-sample interview evidence | `reports/final/results/interview_market_validation.md`; `reports/final/appendix/interview_validation.tex`. |
| 70% of interviewees preferred PaperMemory-provided API/model access through monthly subscription rather than BYOK-only setup. | Supported as convenience-sample interview evidence | Same as above; commercial framing is provider-compliant API relay, not account-pool resale. |
| The interview evidence is auditable as an aggregate-only short questionnaire protocol. | Supported as protocol and aggregate notes, not participant-level raw data | `reports/final/appendix/interview_validation.tex`; `reports/final/results/interview_market_validation.md`. |
| Elicit and Consensus are market comparators for evidence-oriented research workflows. | Supported as market-context citation, not feature parity | `elicitPricing`, `consensusPricing`, and the Node 9 source snapshot in `reports/final/results/cost_benefit.md`. |
| The proposed freemium BYOK plus 10 and 20 USD/month tiers are commercially plausible under weekly capped, provider-compliant managed-LLM API relay assumptions. | Supported as proposed packaging, not validated revenue | `reports/final/tables/revenue_model.tex`; `reports/final/tables/pricing_tiers.tex`; `reports/final/tables/tier_economics.tex`; `reports/final/results/cost_benefit.md`. |
| PaperMemory is a compound AI system rather than a simple chat interface. | Supported by architecture artifacts | `reports/final/results/evidence_contract.md`, `reports/final/results/chat_ui_packet.md`, `reports/final/results/evidence_reliability_layer.md`, `reports/final/figures/pipeline.tex`. |
| PaperMemory turns retrieved pages into validated EvidencePackets before chat/report use. | Supported | `reports/final/results/evidence_contract.md`, `reports/final/results/chat_ui_packet.md`. |
| PaperMemory provides bounded agentic autonomy through query rewrite, retrieval, coverage-gated retry, stop reasons, and packet-grounded answers. | Supported | `reports/final/results/agent_trace_examples.md`, `reports/final/tables/agent_trace_summary.tex`, `reports/final/results/live_local_test_log.md`. |
| PaperMemory exposes reliability status as strong, partial, or insufficient. | Supported | `reports/final/results/evidence_reliability_layer.md`; backend reliability tests listed in planning/progress artifacts. |
| The report includes an executable weak keyword-overlap baseline on the same synthetic fixture questions. | Supported within synthetic boundary | `eval/retrieval/results/keyword-baseline.json`; `eval/retrieval/results/keyword-baseline.csv`; `eval/retrieval/results/keyword-baseline.md`; `reports/final/results/keyword_baseline_metrics.md`. |
| The current package contributes selectable-text BM25 support. | Supported | `reports/final/results/text_manifest_quality.md`, `reports/final/results/bm25_metrics.md`, `eval/retrieval/results/bm25-baseline.csv`. |
| The current package contributes page-canonical hybrid fusion. | Supported | `reports/final/results/hybrid_metrics.md`, `eval/retrieval/results/hybrid-baseline.csv`. |
| BM25 improves Recall@1 from 77.8% to 88.9% on the fixture suite. | Supported within synthetic boundary | `reports/final/results/baseline_metrics.md`, `reports/final/results/bm25_metrics.md`. |
| BM25 improves retrieval-level refusal correctness from 33.3% to 100.0% on the fixture suite. | Supported within synthetic boundary | Same as above; refusal is retrieval-level, not answer-level. |
| Hybrid fusion preserves page-canonical trace coverage rather than proving real-corpus gains. | Supported and intentionally bounded | `reports/final/results/hybrid_metrics.md` records 27 both-trace units and repeats the synthetic boundary. |
| Robustness fixtures cover empty scope, missing evidence, repeated retrieval, prompt-injection-like PDF text, citation drift, conflicting numeric evidence, and low-text markers. | Supported | `reports/final/results/robustness_matrix.md`, `reports/final/results/failure_gallery.md`. |
| The commercial stress test estimates positive base-case net savings for first-pass evidence gathering under stated assumptions. | Supported as planning estimate | `reports/final/results/cost_benefit.csv`, `reports/final/results/cost_benefit.md`, `reports/final/tables/cost_summary.tex`. |
| Visual document retrieval systems motivate page-image handling for visually rich PDFs. | Supported by external citations | VisRAG and ColPali references in `references.bib` and inline bibliography. |
| BM25 and RRF are standard retrieval/fusion references for lexical retrieval and rank fusion. | Supported by external citations | Robertson and Zaragoza 2009; Cormack, Clarke, and Buettcher 2009. |
| A separate three-minute demo video accompanies submission; the PDF focuses on report evidence rather than road-show scene mapping. | Supported as report scope boundary, not local video-file verification | `reports/final/main.tex`; `reports/final/checklist.md`; `reports/final/build_notes.md`. |
| The report does not claim real-corpus retrieval superiority, OCR robustness, dense semantic retrieval, full literature-review automation, comprehensive security, or validated product-market fit. | Supported as boundary statement | Main report limitations, appendix, and this claim map. |

Unsupported or future-work claims intentionally excluded:

- Actual paid conversion, retention, referral, or production revenue.
- Proven product-market fit.
- Real user productivity gains after repeated use.
- Broad real-corpus retrieval quality.
- OCR robustness.
- Dense semantic text retrieval.
- Exhaustive systematic-review automation.
- Broad prompt-injection or security assurance.
- Feature parity with Elicit, Consensus, or other commercial systems.
