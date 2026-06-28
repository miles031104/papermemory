# PaperMemory Final Report Section Plan

Purpose: use this document together with `.planning/2026-06-27-paper-memory-report-brainstorm/` to guide the next report rewrite. The report is a course deliverable in NeurIPS style, not a formal NeurIPS submission. We should keep academic clarity and claim-evidence discipline, but we can write more boldly about product value when the claim is backed by interviews, cost modeling, or live demo evidence.

## Scoring Strategy

| Criterion | Weight | Report implication |
| --- | ---: | --- |
| Formatting | 12.5% | Keep official NeurIPS LaTeX style, compile a single PDF, keep main body within nine pages, and preserve references, appendix, and checklist order. |
| Technical Depth | 25% | Make the compound AI architecture explicit: PDF rendering/text extraction, visual retrieval, BM25, RRF fusion, EvidencePacket schema, bounded orchestrator, reliability layer, UI, and cost model. |
| Market Proof | 25% | Move market need, willingness-to-pay evidence, and revenue logic into the front half of the paper. Use interview evidence and the cost-benefit model together. |
| Communication | 25% | Tell one coherent story: researchers pay for trustworthy first-pass evidence gathering because citations, uncertainty, and verification cost are painful. Use clean tables and a strong architecture figure. |
| Road Show | 12.5% | Ensure checklist compliance and make every report claim match a visible 3-minute demo moment. |

## High-Level Paper Thesis

PaperMemory is a local-first compound AI research assistant for postgraduate researchers who need faster, more trustworthy first-pass evidence gathering from PDF collections. It is not merely a chat interface: it builds EvidencePackets from page-level retrieval, runs a bounded evidence-seeking loop, checks reliability, exposes traceable limits, and supports a freemium BYOK plus paid API/model-access subscription model.

The report should make three claims prominently:

1. Market need exists: 10 postgraduate interviewees reported a mean 4.2/5 conditional purchase likelihood, and 70% preferred product-provided API/model access through monthly subscription over a BYOK-only workflow.
2. Technical depth exists: PaperMemory integrates retrieval, evidence validation, agentic orchestration, reliability checking, UI evidence surfacing, and cost modeling into a compound system.
3. Commercial feasibility is plausible: the cost stress test suggests API/token cost is small relative to saved expert labor in several first-pass evidence scenarios, while preserving human verification.

## Main Body Section Plan

Target: 7 to 8 main-body pages before references. This gives enough space for market proof and communication while staying under the nine-page limit.

### Abstract

Goal: summarize problem, market evidence, compound AI solution, evaluation, robustness, and commercial stress test in one paragraph.

Required messages:

- PDF literature workflows are slow because retrieval, citation support, and uncertainty are hidden.
- PaperMemory solves this with page-level EvidencePackets, bounded evidence seeking, and reliability status.
- Market signal: 10 postgraduate interviews, 4.2/5 conditional purchase likelihood, 70% API/subscription preference.
- Technical result: BM25 improves fixture Recall@1 from 77.8% to 88.9% and refusal correctness from 33.3% to 100.0%; robustness fixtures cover missing evidence, citation drift, prompt-injection-like PDF text, conflicts, and low-text pages.
- Commercial result: cost stress test estimates positive base-case net savings for first-pass evidence gathering, with human verification still required.

Evidence:

- `reports/final/results/bm25_metrics.md`
- `reports/final/results/robustness_matrix.md`
- `reports/final/results/evidence_reliability_layer.md`
- `reports/final/results/cost_benefit.md`
- interview aggregate from planning notes

Boldness boundary:

- We may call the market signal "early willingness-to-pay evidence."
- Do not call it proven revenue, retention, or product-market fit.

### 1. Introduction: Market Need and Opportunity

Goal: win Market Proof and Communication points early.

Paragraph roles:

1. Opening problem: postgraduate researchers waste time turning PDFs into trustworthy citation-backed claims.
2. Market validation: report the 10-person interview result and what it implies.
3. Product gap: existing literature tools are useful, but PaperMemory focuses on local PDF collections, visible evidence packets, and BYOK or hosted model access.
4. Contributions: list technical, reliability, and commercial contributions.

Required evidence:

- Interview aggregate: n=10 PhD/master's students, 4.2/5 conditional purchase likelihood, 70% API/subscription preference.
- Cost stress test and BLS wage assumptions.
- Competitor context: Elicit and Consensus as market comparators, not feature-parity baselines.

Visual/table:

- Add a small "Market validation snapshot" table in the main text or appendix:
  - Sample: 10 postgraduate researchers.
  - Conditional purchase likelihood: 4.2/5.
  - API/subscription preference: 70%.
  - Preferred product model: free BYOK tier plus paid hosted/model-access tiers.

Claim boundary:

- Say "early evidence of willingness to pay among a small convenience sample."
- Do not say "validated market demand" unless clearly bounded.

### 2. Product Boundary and Revenue Logic

Goal: make the "Profit Logic" unmissable.

Paragraph roles:

1. Target users and workflow: postgraduate researchers, literature-heavy R&D teams, and consulting/research groups.
2. Free tier: BYOK version with limited groups, for example 3 groups, to reduce adoption friction.
3. Paid tiers: 10 USD/month and 20 USD/month API/model-access subscriptions with included model usage.
4. Why users pay: convenience, fewer API setup barriers, centralized model access, evidence-management workflow, and time savings.
5. Non-goals: not a full systematic-review replacement, not final expert adjudication, not guaranteed ROI.

Required evidence:

- Interview result: 70% prefer provided API/model access.
- `reports/final/results/cost_benefit.md`
- `reports/final/tables/cost_summary.tex`
- competitor pricing context from Node 9 source snapshot

Visual/table:

- Add a "Revenue model and value logic" table:
  - Free BYOK: limited groups, no included model spend.
  - 10 USD/month: lower included model usage, more groups.
  - 20 USD/month: higher included model usage, larger workspace.
  - Cost rationale: per-run API cost is small in current stress scenarios.

Claim boundary:

- We can be bold about the planned business model.
- We must say the tiers are proposed, not launched or revenue-generating.

### 3. Compound AI System Architecture

Goal: score Technical Depth by showing this is more than a chat wrapper.

Paragraph roles:

1. Architecture overview: PDF ingestion to page images/text manifests to retrieval to EvidencePackets to chat/report UI.
2. Component integration: visual retrieval, BM25, RRF fusion, Qdrant/vector layer where applicable, LLM generation, UI evidence panel, cost model.
3. EvidencePacket contract: stable evidence IDs, paper IDs, page numbers, source modality, validation state, citations, limits, and public-safe traces.
4. Why compound: each component reduces a different failure mode: visual layout, exact terms, citation grounding, bounded retries, reliability status, and user verification.

Required evidence:

- `reports/final/results/evidence_contract.md`
- `reports/final/results/chat_ui_packet.md`
- `reports/final/results/evidence_reliability_layer.md`
- `reports/final/figures/pipeline.tex`
- `reports/final/tables/milestones.tex`

Visual/table:

- Update pipeline figure to include the reliability layer:
  - Requirement planning.
  - Coverage check.
  - Claim verification.
  - Reliability status: strong, partial, insufficient.

Claim boundary:

- Say "compound AI system" and "bounded autonomous agent."
- Do not say "general autonomous research scientist" or "full AGI."

### 4. Agentic Autonomy and Implementation Logic

Goal: directly address the assignment's "Autonomous Agent" requirement.

Paragraph roles:

1. Autonomy definition: not open-ended chat, but a server-verified state machine that plans evidence needs and stops safely.
2. Multi-step loop: query rewrite, first retrieval, evidence analysis, targeted second retrieval, sufficiency check, answer generation.
3. Self-correction: coverage-gated retries attempt to fill missing evidence instead of blindly answering.
4. Reliability layer: requirement planner, coverage evaluator, claim verifier, and response-level reliability status.
5. Generalization: diverse paper scopes, visual and text evidence, missing evidence, numeric conflicts, prompt-injection-like text, and low-text pages.

Required evidence:

- `reports/final/results/agent_trace_examples.md`
- `reports/final/results/evidence_reliability_layer.md`
- `reports/final/results/live_local_test_log.md`
- `apps/api/tests/test_research_orchestrator.py`
- `apps/api/tests/test_evidence_reliability_eval.py`

Visual/table:

- Add or revise a trace table:
  - State.
  - Agent action.
  - Tool/component used.
  - Stop condition.
  - Safety boundary.

Claim boundary:

- Strong wording allowed: "agentic autonomy beyond a simple chat UI."
- Keep the modifier "bounded" whenever describing autonomy.

### 5. Baselines, Evaluation, and Technical Results

Goal: satisfy Technical Depth and show enough comparison for the assignment.

Paragraph roles:

1. Explain evaluation setup: synthetic/local controlled fixtures and live local controlled corpus.
2. Baseline comparison: visual API baseline, BM25 text manifest, hybrid page fusion, qualitative GPT/manual narrative baseline.
3. Results: BM25 improves exact-term and refusal behavior; hybrid adds trace coverage; live local test shows end-to-end evidence workflow.
4. Interpretation: results support implementation soundness and workflow feasibility, not real-corpus dominance.

Required evidence:

- `reports/final/results/baseline_metrics.md`
- `reports/final/results/bm25_metrics.md`
- `reports/final/results/hybrid_metrics.md`
- `reports/final/results/comparison_matrix.md`
- `reports/final/results/live_local_test_log.md`
- `eval/retrieval/results/*.csv`

Visual/table:

- Keep retrieval summary table.
- Add "Comparator boundary" column if GPT/manual baseline is included.

Boldness boundary:

- It is acceptable for this assignment to call the current evaluation "a proof-of-capability evaluation."
- Do not call it a broad benchmark.

### 6. Trust, Safety, and Robustness

Goal: make commercial robustness visible.

Paragraph roles:

1. Trust problem: commercial users need failure behavior, not just good answers.
2. Robustness cases: empty scope, missing evidence, repeated retrieval, prompt-injection-like PDF text, citation drift, conflicting numeric evidence, low-text pages.
3. Reliability status: strong, partial, insufficient gives users an action signal.
4. Safety model: PDF text is evidence, not instruction; public traces avoid leaking local paths or unsafe planner hints.
5. Limit: deterministic robustness package, not comprehensive adversarial security.

Required evidence:

- `reports/final/results/robustness_matrix.md`
- `reports/final/results/failure_gallery.md`
- `reports/final/results/evidence_reliability_layer.md`
- `reports/final/results/live_local_test_log.md`
- `apps/api/tests/test_prompt_injection_pdf.py`
- `apps/api/tests/test_retrieval_robustness.py`

Visual/table:

- Keep robustness table.
- Add one short "failure behavior" row for reliability status if space allows.

Claim boundary:

- Use commercial phrasing: "designed for safer review workflows."
- Avoid "secure against all prompt injection."

### 7. Commercial Stress Test

Goal: make cost-benefit analysis concrete and connected to pricing tiers.

Paragraph roles:

1. Formula: net savings equals saved labor minus operation, verification, API/compute, and license costs.
2. Scenarios: 20-PDF evidence packet, 50-PDF R&D landscape, systematic-review pre-screening.
3. Token/API cost: show per-run or per-scenario cost.
4. Subscription fit: explain why 10 USD/month and 20 USD/month tiers can be plausible only if usage is bounded by included model credits, rate limits, or fair-use policies.
5. Conservative interpretation: some low cases can be negative; human verification remains required.

Required evidence:

- `reports/final/results/cost_benefit.csv`
- `reports/final/results/cost_benefit.md`
- `scripts/estimate_run_cost.py`
- interview API/subscription preference

Visual/table:

- Keep cost summary table.
- Add a small pricing-tier stress row if page budget allows:
  - Free BYOK: zero model liability.
  - 10 USD/month: capped model credits.
  - 20 USD/month: higher credits and more groups.

Claim boundary:

- We can argue "commercially plausible."
- Do not claim profitable at scale without hosting, support, and usage-distribution data.

### 8. Limitations, Ethics, and Reproducibility

Goal: protect claim credibility while satisfying checklist and formatting points.

Paragraph roles:

1. Limitations: synthetic/local fixtures, no real-corpus benchmark, no OCR robustness, no dense semantic text retrieval, no actual paid conversion.
2. Ethics/privacy: BYOK/local-first reduces some centralization risks but external APIs may still be used.
3. Licensing: PyMuPDF/MuPDF licensing needs deployment review.
4. Reproducibility: repo, environment, tests, artifacts, PDF build, page count.
5. Checklist: answers are honest and easy to find.

Required evidence:

- `reports/final/build_notes.md`
- `reports/final/checklist.md`
- `reports/final/appendix/reproducibility.tex`
- `reports/final/claim_evidence_map.md`

Required fix:

- Update reproducibility path from the old `D:/codex/llm_paper_assis/papermemory` root to the active `D:/codex/papermemory`, or explain that the old path is now a junction.

Claim boundary:

- Honest limitations are valuable, but do not let this section undercut the product. Phrase limitations as next commercialization milestones.

### 9. Conclusion

Goal: close with the scoring thesis.

Paragraph roles:

1. Restate paid problem and market signal.
2. Restate compound/agentic solution.
3. Restate trust and cost evidence.
4. End with next steps: real-corpus evaluation, subscription usage calibration, OCR/dense retrieval expansion, and road-show demo.

Required evidence:

- Claim-evidence map.
- Interview aggregate.
- Cost-benefit base cases.
- Reliability and robustness artifacts.

Claim boundary:

- No new claims in the conclusion.

## Appendix Plan

Appendices should carry detail without stealing main-body space.

| Appendix item | Purpose | Source |
| --- | --- | --- |
| Interview validation | Market proof details: sample, question wording, 4.2/5 mean, 70% API/subscription preference, limitations. | User-provided interview aggregate, plus any anonymized notes added later. |
| Reproducibility | Commands, environment, repository state, build notes, page count. | Existing appendix and build notes. |
| Full metrics | Retrieval CSVs, robustness counts, controlled live local test caveats. | `reports/final/results/`, `eval/retrieval/results/`. |
| Cost assumptions | Token pricing, wage assumptions, formula, sensitivity rows, licensing risk. | `cost_benefit.md`, `cost_benefit.csv`. |
| NeurIPS-style checklist | Checklist compliance for the assignment. | Existing checklist section. |

## Visual And Table Checklist

Must-have:

- Pipeline figure with reliability layer included.
- Market validation snapshot table.
- Retrieval/baseline comparison table.
- Robustness/failure behavior table.
- Cost-benefit and pricing-tier stress table.

Quality rules:

- Every table caption should say what conclusion the reader should draw.
- Every metric table needs a boundary column if the data are synthetic or controlled.
- Avoid crowded tables. Put raw rows in appendix.

## Claim Posture For This Assignment

Use stronger product language than the current conservative report:

- Good: "PaperMemory targets a paid postgraduate research workflow validated by early interview evidence."
- Good: "The system demonstrates agentic autonomy beyond a chat interface through bounded evidence planning, retrieval, verification, and stop conditions."
- Good: "The proposed freemium BYOK plus 10/20 USD subscription model is commercially plausible under bounded usage and the current cost stress test."

Avoid overclaiming:

- Bad: "PaperMemory has proven product-market fit."
- Bad: "PaperMemory replaces systematic reviews."
- Bad: "PaperMemory is secure against prompt injection."
- Bad: "The benchmark proves real-corpus retrieval superiority."

## Next Report Actions

1. Create or update an interview-market artifact under `reports/final/results/`.
2. Add a LaTeX market validation table.
3. Revise `main.tex` to follow this section order and scoring logic.
4. Integrate the evidence reliability layer into architecture, autonomy, and robustness sections.
5. Add the planned free BYOK, 10 USD/month, and 20 USD/month revenue model.
6. Update the cost section to connect subscription price, model usage, and human-labor savings.
7. Fix reproducibility path mismatch.
8. Compile PDF and verify page count, checklist placement, and source/PDF scans.
9. Align `demo/script.md` with the final report claims.

## Acceptance Checklist Before Final Draft

- Formatting: PDF compiles, main body <= 9 pages, references and appendix after conclusion, checklist present.
- Technical Depth: architecture, algorithms, tools, prompts/state machine, and reliability layer are all described.
- Market Proof: interview evidence, pricing model, competitor context, and cost-benefit model are visible in the main body.
- Communication: abstract and introduction tell the paid problem, solution, and evidence clearly; all visuals have useful captions.
- Road Show: every demo claim has a matching report artifact or live screen moment.
- Claim Evidence: every abstract and introduction claim appears in `claim_evidence_map.md`.
