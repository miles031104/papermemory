# PaperMemory Node 9 Commercial Stress Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn PaperMemory's existing evidence-packet, retrieval, orchestrator, and robustness outputs into a transparent commercial stress test: per-run cost assumptions, human-time savings scenarios, sensitivity ranges, and a short demo close.

**Architecture:** Node 9 is a report/artifact layer over Nodes 1-8. It must not change retrieval, chat, orchestrator, evidence validation, robustness behavior, or frontend product surfaces. It adds a deterministic cost-estimation script and report-ready outputs that explain the business value of first-pass evidence gathering and citation packaging.

**Tech Stack:** Python 3.12 standard library, CSV/Markdown artifacts, existing `reports/final/results/` evidence, existing `demo/shot-list.md`.

---

## Stage Boundary

Node 9 is commercial stress testing only. It must not implement Node 10 final report writing, Node 11 video production, product pricing UI, payment/billing, new retrieval algorithms, OCR, dense text embeddings, frontend redesign, or broad claim expansion. It may add a small standalone script, focused tests for that script, cost-benefit CSV/Markdown outputs, and one demo cost-panel beat.

## Current Baseline Findings

- Remote baseline was refreshed before planning. `HEAD`, `origin/miles`, and merge-base are all `6884d738df9d685bad4f5a673a7d13a7bc2fb691`.
- Nodes 1-8 are complete or accepted with recorded boundaries. The latest Node 8 focused robustness verification is `11 passed`.
- No existing cost model script exists under `scripts/`; `reports/final/results/` already contains metrics, trace, robustness, environment, and UI packet artifacts that Node 9 can reference.
- Node 9 should compute scenario economics from transparent assumptions rather than inventing production telemetry that the app does not currently record.

## Refreshed External Source Snapshot

These source checks were refreshed on 2026-06-24 and must be cited in `cost_benefit.md`:

- OpenAI API pricing: `https://openai.com/api/pricing/`
  - GPT-5.4 mini standard rates shown on the page: input `$0.75 / 1M tokens`, cached input `$0.075 / 1M tokens`, output `$4.50 / 1M tokens`.
  - Batch API is shown as saving 50% on inputs and outputs.
- BLS Occupational Outlook Handbook:
  - Management analysts: `https://www.bls.gov/ooh/business-and-financial/management-analysts.htm`, median annual wage `$101,190` in May 2024.
  - Data scientists: `https://www.bls.gov/ooh/math/data-scientists.htm`, median annual wage `$112,590` in May 2024.
  - Medical scientists: `https://www.bls.gov/ooh/life-physical-and-social-science/medical-scientists.htm`, median annual wage `$100,590` in May 2024.
- Competitor/context pricing:
  - Elicit pricing: `https://elicit.com/pricing`, Pro/Scale annual billing values are visible; systematic-review and team tiers should be treated as market context, not direct feature parity.
  - Consensus subscription plans: `https://help.consensus.app/en/articles/10087865-subscription-plans`, Pro and Deep prices plus review quotas are visible; treat as market context only.

If any source changes during implementation, record the refreshed value and date in the Markdown instead of using this snapshot blindly.

## File Map

- Create: `scripts/estimate_run_cost.py`
  - Deterministic cost model with scenario assumptions, formula functions, CSV/Markdown writers, and a CLI.
- Create if useful: `apps/api/tests/test_estimate_run_cost.py`
  - Focused tests for the cost formulas, sensitivity ranges, and generated CSV shape.
- Create: `reports/final/results/cost_benefit.csv`
  - Machine-readable scenario rows.
- Create: `reports/final/results/cost_benefit.md`
  - Human-readable assumptions, formula, source links, sensitivity table, and bounded interpretation.
- Update: `demo/shot-list.md`
  - Add one short ROI/cost-panel demo beat for the road-show close.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - Record commands, review outcomes, refreshed sources, and boundaries.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`
  - Move Node 9 through `stage_plan_ready`, `in_progress`, and review statuses.

## Cost Model Requirements

The model must be transparent and reproducible:

1. Use scenario rows for:
   - 20-PDF evidence packet.
   - 50-PDF consulting/R&D landscape.
   - Systematic-review pre-screening.
2. Use a bounded formula:

```text
net_savings = (manual_hours - papermemory_hours - verification_hours) * fully_loaded_hourly_rate - api_or_compute_cost - license_cost
```

3. Include low/base/high sensitivity cases for manual hours and verification hours.
4. Include AI/API cost using configurable token counts and per-1M-token rates.
5. Include labor assumptions derived from BLS annual wages converted to hourly with a documented divisor and an explicit fully-loaded multiplier.
6. Include license/subscription assumptions as variables or scenario columns, not hidden constants.
7. Mark all values as planning estimates unless they come from actual local artifacts.

## Claim Boundaries

Node 9 may claim:

- PaperMemory can be positioned around first-pass evidence gathering, citation packaging, and human verification.
- Under stated assumptions, scenarios can show positive or negative net savings.
- API/token cost is small relative to expert labor in many plausible cases, but not always.

Node 9 must not claim:

- Guaranteed ROI.
- Direct replacement for systematic reviews.
- Feature parity with Elicit, Consensus, or enterprise literature-review products.
- Production cost telemetry if only estimates are available.
- Customer willingness to pay or validated market demand.

## Task Plan

### Task 1: Cost Model Script

**Files:**
- Create: `scripts/estimate_run_cost.py`
- Create if useful: `apps/api/tests/test_estimate_run_cost.py`

- [ ] Define dataclasses or plain dictionaries for model pricing, labor assumptions, and scenario assumptions.
- [ ] Implement formula functions for API cost, hourly conversion, fully loaded hourly cost, and net savings sensitivity.
- [ ] Include default scenarios for 20-PDF, 50-PDF, and systematic-review pre-screening cases.
- [ ] Provide a CLI that writes `reports/final/results/cost_benefit.csv` and `reports/final/results/cost_benefit.md`.
- [ ] Keep the script standard-library only.
- [ ] Add focused tests for at least formula correctness, sensitivity ordering, and CSV columns.

### Task 2: Cost-Benefit Artifacts

**Files:**
- Create: `reports/final/results/cost_benefit.csv`
- Create: `reports/final/results/cost_benefit.md`

- [ ] Generate the CSV from the script, not by hand.
- [ ] Include columns for scenario, paper count, assumed query/run count, input/output tokens, API cost, manual hours low/base/high, PaperMemory operation hours, verification hours low/base/high, labor profile, fully loaded hourly rate, license cost, net savings low/base/high, and source notes.
- [ ] In Markdown, include the formula, refreshed source links, exact assumptions, sensitivity table, and one short interpretation per scenario.
- [ ] State that competitor prices are market context, not a direct apples-to-apples benchmark.
- [ ] State that PyMuPDF/MuPDF licensing remains a commercialization risk if AGPL obligations or commercial licensing matter in deployment.

### Task 3: Demo Cost Beat

**Files:**
- Modify: `demo/shot-list.md`

- [ ] Add a concise Node 9 segment after the robustness/safety beat.
- [ ] The beat should explain the business value in under 20 seconds: evidence packet cost, saved expert time, verification time, and bounded ROI.
- [ ] Keep narration bounded to first-pass evidence gathering and citation packaging.

### Task 4: Required Verification

**Files:** no direct code edits.

- [ ] Run cost model tests:

```powershell
python -m pytest apps/api/tests/test_estimate_run_cost.py -q
```

- [ ] Run the script and verify generated artifacts:

```powershell
python scripts/estimate_run_cost.py --write-reports
```

- [ ] Run a focused artifact smoke check:

```powershell
python - <<'PY'
from pathlib import Path
for path in [
    Path('reports/final/results/cost_benefit.csv'),
    Path('reports/final/results/cost_benefit.md'),
]:
    assert path.exists() and path.stat().st_size > 0, path
print('cost artifacts present')
PY
```

- [ ] Run existing Node 8 focused robustness tests to guard against accidental edits:

```powershell
python -m pytest apps/api/tests/test_prompt_injection_pdf.py apps/api/tests/test_retrieval_robustness.py -q
```

- [ ] Run diff hygiene:

```powershell
git diff --check
```

## Subagent Plan

### Subagent A: Node 9 Commercial Stress Test Implementer

**Role:** worker.

**Write scope:** `scripts/estimate_run_cost.py`, optional focused test file, `reports/final/results/cost_benefit.csv`, `reports/final/results/cost_benefit.md`, `demo/shot-list.md`, and the Node 9 planning status entries.

**Task:** Implement the deterministic cost model, generate the CSV/Markdown artifacts, and update the demo shot list. Use the refreshed source snapshot above unless implementation-time browsing shows a source changed. Do not modify retrieval, chat, orchestrator, evidence validation, frontend UI, Node 10 report files, or Node 11 video artifacts.

### Subagent B: Node 9 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Verify implementation matches this stage plan:

- The three required scenarios exist.
- Cost model includes API/compute cost, human verification time, and fully loaded labor assumption.
- Markdown cites refreshed source links and states assumptions clearly.
- Claims remain bounded to first-pass evidence gathering and citation packaging.
- Node 10 and Node 11 work are not implemented prematurely.

### Subagent C: Node 9 Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check maintainability and business-claim quality:

- Script is deterministic, simple, standard-library only, and testable.
- CSV shape is stable for report ingestion.
- Sensitivity logic is understandable and does not hide magic constants.
- Competitor pricing is used as context only.
- Residual risks such as licensing, customer willingness to pay, and stale pricing are explicit.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 9:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 9 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 9 Gate

Node 9 is accepted only when:

- Required verification commands pass.
- Spec review passes.
- Quality review passes.
- `cost_benefit.csv` and `cost_benefit.md` exist and are generated from the script.
- Demo shot list includes one ROI/cost-panel beat.
- Claims stay bounded to first-pass evidence gathering and citation packaging.
- The next stage remains Node 10: Final report package.
