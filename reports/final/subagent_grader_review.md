# Cold Grader Review and Next Optimization Plan

Date: 2026-06-27

Reviewer setup: a cold-start subagent was given only the assignment requirements, scoring rubric, current report/demo artifact paths, and an instruction not to edit files. It did not inherit the prior conversation or previous main-agent judgement.

## Blind Review Score

Overall score: **80 / 100**.

| Criterion | Weight | Blind score | Main implication |
| --- | ---: | ---: | --- |
| Formatting | 12.5 | 11.5 | Strong enough. Only minor risk around dense layout and PDF order interpretation. |
| Technical Depth | 25.0 | 19.5 | Architecture is clear, but evaluation is small, synthetic/local, and baselines are limited. |
| Market Proof | 25.0 | 18.0 | Interview evidence is useful, but too aggregate and not auditable enough. |
| Communication | 25.0 | 21.0 | Flow is good. Visuals/tables are professional but dense and table-heavy. |
| Road Show | 12.5 | 10.0 | Script/checklist exist, but no visible video link, screenshots, or public repo/data handoff. |

## Key Grader Objections

1. **Evaluation is too synthetic to prove real-world performance.** The current suite is small and explicitly bounded. This is honest, but it caps Technical Depth.
2. **Market proof is directionally useful but thin.** The 10-person interview aggregate supports early willingness to pay, but a grader cannot audit the protocol, distribution, or raw responses from the current PDF alone.
3. **Commercial stress test is plausible but not yet a business case.** Token/API costs and labor savings are visible, but tier economics need hosting, support, licensing, heavy-user caps, and gross-margin sensitivity.
4. **Baseline comparison is not fully fair or executable.** The report has strong internal retrieval baselines, but the GPT-only/manual narrative row uses N/A metrics, and market competitors are not evaluated.
5. **Appendix is useful but not self-contained enough for reproduction.** It records commands and local paths, but not enough dataset samples, traces, interview protocol, or demo evidence for a skeptical reader.

## Brainstormed Optimization Routes

### Route A: Highest Score Gain, Requires New Evaluation

Goal: raise the report from a strong course submission to a much more empirically convincing one.

Expected score gain: **+6 to +8 points**.

Work:

- Build a small real-corpus benchmark with 20-50 real PDFs.
- Add human-labeled page evidence for each question.
- Measure answer-level correctness, citation support, refusal correctness, and page-evidence precision/recall.
- Compare PaperMemory against plain chatbot, simple text RAG, BM25-only, visual/page mode, and hybrid mode.
- Add one concise table to Section 5 and move detailed samples/traces to the appendix.

Risk:

- This is the best technical improvement, but it is also the most expensive and easiest to under-finish.
- If time is short, a small but auditable 10-20 PDF benchmark may be better than an ambitious 50-PDF benchmark.

### Route B: Fast Rubric Lift Without Major New System Work

Goal: use existing work plus small additional artifacts to recover points in Market Proof, Road Show, and Commercial Stress Test.

Expected score gain: **+8 to +13 points combined** if executed cleanly.

Work:

1. Make interview evidence auditable.
   - Add anonymized participant rows, interview questions, response distribution, WTP bands, competitor/tool usage, and 3-5 short paraphrased quotes.
   - Update `reports/final/results/interview_market_validation.md`, `reports/final/appendix/interview_validation.tex`, and optionally `reports/final/tables/market_validation.tex`.
   - Expected gain: +3 to +5.

2. Turn pricing into tier economics.
   - Add quota assumptions for free BYOK, 10 USD/month, and 20 USD/month.
   - Add gross-margin and break-even sensitivity under light/base/heavy usage.
   - Include hosting/support/license assumptions and an explicit heavy-user cap.
   - Update `reports/final/results/cost_benefit.md`, `reports/final/tables/pricing_tiers.tex`, `reports/final/tables/cost_summary.tex`, and the commercial stress-test paragraph.
   - Expected gain: +3 to +4.

3. Strengthen competitor and baseline framing.
   - Add a feature matrix for Elicit, Consensus, NotebookLM/Zotero-like workflows, simple RAG/chatbot, and PaperMemory.
   - If feasible, run one executable simple-RAG or GPT-only baseline on the same fixture questions instead of using N/A.
   - Update `reports/final/tables/retrieval_summary.tex` or create a compact competitor/baseline table.
   - Expected gain: +2 to +3.

4. Improve road-show evidence.
   - Add screenshot sequence, an available video link or explicit no-video note, demo fallback assets, and a one-page mapping from demo scenes to implemented artifacts.
   - Update `demo/script.md`, `demo/shot-list.md`, and an appendix/demo evidence note.
   - Expected gain: +2 to +3.

Risk:

- This route improves grading fit quickly, but it will not fully solve the synthetic-evaluation objection.

### Route C: Hybrid Sprint

Goal: do enough real evaluation to reduce the biggest objection while also adding quick commercial/market evidence.

Recommended if one more focused work session is available.

Order:

1. Add auditable interview appendix.
2. Add tier economics and gross-margin sensitivity.
3. Implement or report a same-fixture simple RAG/GPT-only baseline.
4. Add road-show screenshot/demo evidence.
5. If time remains, run a small real-corpus pilot with 10-20 PDFs and present it as a pilot, not a broad benchmark.

Expected score gain: **+10 to +15 points** with bounded scope.

## Recommended Next Action

Choose **Route C** unless the deadline is extremely close. It attacks the largest grader objections without betting everything on a full new benchmark.

Immediate task order:

1. **Interview audit appendix.** Highest Market Proof return and uses evidence the team already has.
2. **Tier economics.** Directly addresses the profit-logic requirement and the $10/$20 subscription story.
3. **Executable simple baseline.** Replaces the weakest N/A row with a fair same-fixture comparator.
4. **Road-show evidence pack.** Converts the script into visible investor-facing proof.
5. **Optional real-corpus pilot.** Add only if there is enough time to label and verify it cleanly.

## Preserve

- EvidencePacket as the central technical object.
- Bounded autonomy and stop-reason framing.
- Reliability status: strong, partial, insufficient.
- Honest claim boundaries around synthetic/local evidence, early interviews, and planning estimates.
- Cost-benefit framing as a stress test rather than a revenue guarantee.

## Acceptance Gates For The Next Revision

- Main body remains nine pages or fewer before references.
- Any new market claim has an appendix-backed protocol or table.
- Any new pricing claim includes quota, cost, margin, and abuse/heavy-user caveat.
- Any baseline claim is same-fixture and has runnable command or recorded artifact.
- Road-show section points to actual screenshots, video, or fallback demo assets.
- `main.pdf` compiles and `git diff --check` passes.
