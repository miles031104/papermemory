# Cold Grader Review After Fast Patch

Date: 2026-06-27

Reviewer setup: a fresh subagent was given only the course requirements, scoring rubric, current report artifact paths, and an instruction not to edit files. It did not inherit the earlier repair plan, previous score, or main-agent interpretation.

## Blind Review Score

Overall score: **80 / 100**.

Short verdict: the current report is a strong B+ / borderline A- course submission. The grader considered the system story, bounded autonomy, trust mechanisms, and commercial stress test credible. The remaining deductions are mostly evidence maturity rather than broken formatting or missing sections.

| Criterion | Weight | Blind score | Grader rationale |
| --- | ---: | ---: | --- |
| Formatting and adherence | 12.5 | 11.5 | NeurIPS-style PDF, ordered report/references/appendix/checklist, main body within nine pages. Minor risk remains around anonymous-submission boilerplate and line numbers. |
| Technical depth / AGI implementation | 25.0 | 19.5 | Architecture is solid: EvidencePackets, BM25, hybrid fusion, bounded retry, reliability status, and UI evidence. Deductions come from mostly synthetic/local evaluation and weak competitor baselines. |
| Market proof | 25.0 | 17.5 | The n=10 interview signal is useful and carefully bounded, and it supports the BYOK / 10 USD / 20 USD tier story. Deductions come from small sample size, aggregate-only evidence, and conditional intent rather than paid demand. |
| Communication | 25.0 | 21.0 | Abstract, limitations, and flow from problem to architecture to cost are clear. Some figures and tables feel dense rather than road-show polished. |
| Road show / reproducibility | 12.5 | 10.0 | Reproducibility appendix, checklist, script, shot list, and evidence map are good. Deduction remains because the package is recorder-ready, not an actual completed three-minute video. |

## Top Grader Objections

1. **Technical evaluation is still too synthetic.** Section 5 has only four synthetic papers, twelve pages, twelve golden questions, and three negative questions. This is honest, but it caps the technical score.
2. **Market proof is early intent, not demand validation.** The report uses only n=10, 4.2/5 conditional purchase likelihood, and 70% managed-access preference. This avoids overclaiming, but cannot prove paid demand, retention, or product-market fit.
3. **Subscription economics do not yet connect tiers to margin tightly enough.** The report has cost-benefit scenarios and qualitative weekly caps, but no tier-specific sensitivity table that maps 10 USD / 20 USD price to assumed usage, model cost, support caveat, and margin range.
4. **No final road-show video exists yet.** The current package is recorder-ready and honest, but a grader may still deduct if they expected a finished three-minute video.
5. **Autonomy is bounded.** This is acceptable and defensible, but a grader looking for broader autonomous tool use may call the system conservative.
6. **Competitor comparison is mostly contextual rather than empirical.** Elicit and Consensus are market comparators, while measured rows are internal fixture variants.
7. **Robustness is deterministic regression evidence, not commercial safety proof.** The report states this boundary, but the commercial trust rubric still rewards stronger adversarial evidence.
8. **Visuals are useful but dense.** The pipeline figure and tables communicate the evidence, but screenshots or a cleaner architecture diagram would make the report feel more investor-ready.

## Main-Agent Interpretation

The fast repair succeeded at removing obvious hard deductions: measured baseline is no longer `N/A`, interview claims are aggregate-only, tier wording no longer promises unlimited inference, and road-show language no longer pretends a final video exists. The blind score staying at 80/100 means the remaining ceiling is not caused by missing boilerplate; it is caused by evidence maturity.

The next optimization should not inflate claims. The safest path is to add bounded, auditable artifacts that look like course-grade proof:

- a tiny real-PDF or semi-real pilot if data can be labeled quickly;
- a tier-economics sensitivity table labeled as planning assumptions, not validated quota policy;
- a small empirical workflow comparator against manual PDF + chatbot if it can be run on the same fixture;
- visible road-show screenshots or the actual recorded video;
- a one-page claim/evidence/boundary table inside the PDF so graders do not need to open the external claim map.

## Next Optimization Plan

### Priority 1: Tier Economics Sensitivity

Expected score gain: +2 to +4, mostly Market Proof and Profit Logic.

Why now: this is the fastest remaining fix because the report already has token-cost scenarios, pricing tiers, and tier-boundary language. The missing piece is a grader-facing table connecting price to assumed usage and margin controls.

Safe implementation:

- Add a table titled something like "Illustrative subscription stress test".
- Use scenario assumptions rather than claiming validated production quota.
- Include columns for tier, monthly price, modeled weekly run band, modeled monthly model cost band, margin risk, over-cap behavior, and caveat.
- Keep the wording explicit: this is a planning stress test pending telemetry, not a production promise.

Constraint: do not invent or present exact weekly quotas as validated policy.

### Priority 2: Road-Show Visual Evidence

Expected score gain: +1.5 to +3, mostly Road Show and Communication.

Why now: a real video is best, but screenshots/storyboard still reduce the "recorder-ready only" weakness.

Safe implementation:

- If a final video is available, add the file/link and update the appendix.
- If not, add three to five screenshot placeholders only if they are generated from real local UI/report artifacts.
- Add a compact storyboard figure or appendix table mapping timestamp, screen, claim, and evidence artifact.

Constraint: do not claim a completed video unless the file exists.

### Priority 3: Claim-Evidence-Boundary Table Inside PDF

Expected score gain: +1 to +2, mostly Communication and Reproducibility.

Why now: the external claim map is strong, but a grader may only read the PDF. A compact in-PDF table makes the evidence discipline visible.

Safe implementation:

- Add a small appendix table with four or five rows: autonomy, retrieval performance, interview demand, subscription logic, robustness.
- For each row, list claim, evidence artifact, and boundary.
- Keep it in appendix if main-body page pressure appears.

### Priority 4: Same-Fixture Manual Workflow Comparator

Expected score gain: +2 to +3, mostly Technical Depth.

Why now: full real-corpus evaluation is expensive, but a simple manual PDF + chatbot workflow comparator can be framed as a workflow baseline if it uses the same questions and clearly recorded timing/accuracy protocol.

Safe implementation:

- Use the existing synthetic fixture questions.
- Compare PaperMemory against a documented manual workflow: open paper, search text, ask generic chatbot, manually verify page.
- Report time-to-evidence and citation-support outcomes if measured.
- Keep Elicit/Consensus as qualitative market comparators, not measured baselines.

Constraint: do not fabricate timings. If no timing run exists, write the protocol only, or do not include it as measured evidence.

### Priority 5: Tiny Real-PDF Pilot

Expected score gain: +3 to +6 if completed cleanly, but highest execution risk.

Why now: this directly attacks the biggest technical objection. It should be attempted only if there is enough time to label it honestly.

Safe implementation:

- Use five to ten real PDFs, not a large benchmark.
- Label twenty to thirty questions with page-level evidence.
- Report it as a pilot, not broad real-world performance.
- Include two failure cases.

Constraint: if labels cannot be audited, do not add the pilot.

## Suggestions To Avoid

- Do not add participant-level interview data, distributions, or quotes unless the team actually has them.
- Do not claim product-market fit, paid conversion, retention, or validated revenue.
- Do not add exact 10 USD / 20 USD weekly quotas as if they are production policy.
- Do not call Elicit or Consensus measured baselines unless the same-task run exists.
- Do not weaken the honest limitations; the grader explicitly liked the conservative claim boundaries.

## Recommended Immediate Next Step

If one more repair sprint is available, do this order:

1. Tier economics sensitivity table.
2. In-PDF claim/evidence/boundary table.
3. Road-show screenshots or actual video reference.
4. Optional same-fixture manual workflow comparator.
5. Optional tiny real-PDF pilot only if labels can be created and checked quickly.

This order maximizes grading lift per hour while preserving the claim boundaries that currently protect the report from credibility loss.
