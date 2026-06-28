# PaperMemory Final Report Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to execute this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the PaperMemory final report so it follows `reports/final/report_section_plan.md`, emphasizes the updated scoring weights, integrates market interview evidence, and remains a compilable NeurIPS-style course report.

**Architecture:** Use subagents for bounded writing slices that produce drafts, tables, and appendix artifacts with disjoint ownership. The main agent integrates those artifacts into `reports/final/main.tex`, applies the `humanizer` review rules, updates the claim-evidence map, compiles the PDF, and records verification.

**Tech Stack:** LaTeX, Markdown evidence artifacts, bundled Tectonic LaTeX helper, local result artifacts under `reports/final/results/`, and the `humanizer` skill for writing review.

---

## Scoring Boundary

The report is a course deliverable in NeurIPS style, not a formal NeurIPS submission. The rewrite should be more product-forward than the current conservative draft while still mapping claims to evidence.

| Criterion | Weight | Rewrite requirement |
| --- | ---: | --- |
| Formatting | 12.5% | Single PDF, NeurIPS style, main body <= 9 pages, references/appendix/checklist order. |
| Technical Depth | 25% | Clear compound AI architecture and bounded agentic autonomy. |
| Market Proof | 25% | Front-half market validation, willingness-to-pay signal, and revenue logic. |
| Communication | 25% | Strong abstract/introduction, readable visuals/tables, coherent flow. |
| Road Show | 12.5% | Checklist and 3-minute demo alignment. |

## Source Inputs

- `reports/final/report_section_plan.md`
- `reports/final/main.tex`
- `reports/final/results/evidence_contract.md`
- `reports/final/results/chat_ui_packet.md`
- `reports/final/results/evidence_reliability_layer.md`
- `reports/final/results/agent_trace_examples.md`
- `reports/final/results/baseline_metrics.md`
- `reports/final/results/bm25_metrics.md`
- `reports/final/results/hybrid_metrics.md`
- `reports/final/results/comparison_matrix.md`
- `reports/final/results/robustness_matrix.md`
- `reports/final/results/failure_gallery.md`
- `reports/final/results/live_local_test_log.md`
- `reports/final/results/cost_benefit.md`
- `reports/final/results/cost_benefit.csv`
- `demo/script.md`
- `demo/shot-list.md`

## Claim Boundaries

Allowed stronger claims:

- PaperMemory targets a paid postgraduate research workflow backed by early interview evidence.
- The system is a compound AI system, not a chat wrapper.
- The system demonstrates bounded agentic autonomy through evidence planning, retrieval, coverage checks, claim verification, and stop reasons.
- The proposed freemium BYOK plus 10/20 USD subscription model is commercially plausible under bounded usage assumptions and current cost stress tests.

Still disallowed:

- Proven product-market fit.
- Actual paid conversion, retention, or production revenue.
- Full systematic-review replacement.
- Comprehensive prompt-injection security.
- Broad real-corpus retrieval superiority.
- OCR or dense semantic text retrieval robustness.

## Task 1: Market Evidence, Revenue Logic, and Front-Matter Draft

**Owner:** Worker subagent.

**Write scope:**
- Create: `reports/final/results/interview_market_validation.md`
- Create: `reports/final/tables/market_validation.tex`
- Create: `reports/final/tables/revenue_model.tex`
- Create: `reports/final/drafts/front_market_revenue.tex`

**Do not edit:** `reports/final/main.tex`.

- [ ] Write a concise interview-market artifact with n=10 postgraduate researchers, 4.2/5 conditional purchase likelihood, 70% API/subscription preference, planned BYOK and 10/20 USD tiers, and limitations.
- [ ] Create a compact LaTeX market validation table.
- [ ] Create a compact LaTeX revenue model table.
- [ ] Draft Abstract, Introduction, and Product Boundary/Revenue Logic paragraphs in LaTeX fragment form.
- [ ] Keep claims bold enough for the course rubric but bounded as early evidence, proposed tiers, and planning estimates.
- [ ] Self-review the draft for claim support and AI-sounding patterns before returning.

## Task 2: Technical Architecture, Autonomy, and Evaluation Draft

**Owner:** Worker subagent after Task 1 completes and passes review.

**Write scope:**
- Create: `reports/final/drafts/technical_autonomy_evaluation.tex`
- Modify: `reports/final/figures/pipeline.tex`
- Create or modify: `reports/final/tables/agent_trace_summary.tex`
- Modify if needed: `reports/final/tables/retrieval_summary.tex`

**Do not edit:** `reports/final/main.tex`.

- [ ] Draft Compound AI System Architecture, Agentic Autonomy, and Baselines/Evaluation sections in LaTeX fragment form.
- [ ] Update the pipeline figure to include the reliability layer: requirement planning, coverage check, claim verification, and reliability status.
- [ ] Add an agent trace summary table if it improves clarity within the page budget.
- [ ] Preserve synthetic/local/controlled evaluation boundaries.
- [ ] Self-review against Technical Depth and Communication criteria.

## Task 3: Robustness, Commercial Stress Test, Appendix, and Road-Show Alignment Draft

**Owner:** Worker subagent after Task 2 completes and passes review.

**Write scope:**
- Create: `reports/final/drafts/robustness_commercial_limits.tex`
- Modify: `reports/final/tables/cost_summary.tex`
- Create: `reports/final/tables/pricing_tiers.tex`
- Create: `reports/final/appendix/interview_validation.tex`
- Modify: `reports/final/appendix/reproducibility.tex`
- Modify if needed: `demo/script.md`

**Do not edit:** `reports/final/main.tex`.

- [ ] Draft Trust/Safety/Robustness, Commercial Stress Test, Limitations/Reproducibility, and Conclusion fragments.
- [ ] Add a pricing-tier table connecting free BYOK, 10 USD/month, and 20 USD/month to bounded model usage.
- [ ] Add an interview-validation appendix section.
- [ ] Fix the reproducibility path mismatch: active root is `D:/codex/papermemory`; older `D:/codex/llm_paper_assis/papermemory` is a junction.
- [ ] Align demo script language with the final report claims if needed.

## Task 4: Main-Agent Integration and Humanizer Review

**Owner:** Main agent.

**Write scope:**
- Modify: `reports/final/main.tex`
- Modify: `reports/final/claim_evidence_map.md`
- Modify: `reports/final/checklist.md`
- Modify: `reports/final/build_notes.md`
- Modify planning files under `.planning/2026-06-27-paper-memory-report-brainstorm/`

- [ ] Integrate the approved fragments and tables into `main.tex`.
- [ ] Apply the `humanizer` skill to remove AI-sounding patterns while preserving academic tone.
- [ ] Ensure no em/en dashes in newly authored prose unless inside source paths or LaTeX syntax where unavoidable.
- [ ] Update the claim-evidence map with market, revenue, reliability, and road-show claims.
- [ ] Update checklist answers for the course report.

## Task 5: Final Verification

**Owner:** Main agent, with reviewer subagents as needed.

- [ ] Compile the final PDF with the bundled LaTeX helper.
- [ ] Verify PDF exists and page count/main-body count stays within requirement.
- [ ] Scan source and extracted PDF text for placeholders, unsupported overclaims, and AI-sounding tells.
- [ ] Run `git diff --check` on report and planning paths.
- [ ] Request final subagent review for rubric fit and humanized writing quality.
- [ ] Record verification in `reports/final/build_notes.md` and planning progress.

## Acceptance Criteria

- `main.tex` follows the section plan and compiles to `main.pdf`.
- Market proof is visible in the main body and supported by an appendix artifact.
- Technical depth covers compound architecture, bounded autonomy, reliability layer, baselines, and robustness.
- Commercial stress test connects per-run cost, labor savings, and proposed 10/20 USD subscriptions.
- The writing is ordered, natural, and free of obvious AI patterns under the `humanizer` checklist.
- The report remains honest about evidence boundaries.
- Demo script and report claims are aligned.
