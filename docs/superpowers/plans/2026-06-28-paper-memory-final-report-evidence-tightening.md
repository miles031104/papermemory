# PaperMemory Final Report Evidence Tightening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the PaperMemory final report score with the smallest credible edits by strengthening subscription unit economics, making claim support visible inside the PDF, and removing unnecessary road-show material from the report because a separate demo video will accompany submission.

**Architecture:** This is a report-polish and evidence-presentation plan, not a product or benchmark redesign. It modifies a small set of LaTeX/Markdown report artifacts, reuses the existing Node 9 cost stress-test outputs, and preserves the current claim boundaries around synthetic evaluation, aggregate-only interviews, planning estimates, and human verification.

**Tech Stack:** NeurIPS LaTeX report, Markdown evidence artifacts, existing Node 9 cost-benefit outputs, bundled Tectonic compile helper, `pypdf` section/page checks, PowerShell/rg QA.

---

## Scope Boundary

Do:

- Add a tier-economics sensitivity table using existing cost stress-test numbers as illustrative planning scenarios.
- Add a compact PDF-visible claim/evidence/boundary table that summarizes the report's defensible results.
- Keep the road-show demo video outside the report package, with at most a short checklist or reproducibility note that a separate three-minute demo accompanies the submission.
- Preserve the aggregate-only interview boundary: `n=10`, `4.2/5`, and `70%` managed-access preference are the only interview facts available.
- Preserve the synthetic/local evaluation boundary.

Do not:

- Invent participant-level interview rows, response distributions, direct quotes, paid conversion, retention, or product-market fit.
- Turn illustrative tier stress cases into promised production quotas.
- Claim validated gross margin, production revenue, or unlimited inference.
- Treat Elicit, Consensus, or generic chat as measured baselines unless a same-fixture run exists.
- Spend report pages on road-show evidence mapping when a demo video will be submitted separately.

## File Map

- Modify: `reports/final/tables/tier_economics.tex`
  Replace the qualitative tier table with an illustrative subscription sensitivity table derived from existing Node 9 cost scenarios.
- Modify: `reports/final/results/cost_benefit.md`
  Add the same tier-sensitivity assumptions and caveats in Markdown.
- Create: `reports/final/tables/claim_evidence_boundary.tex`
  Add a compact PDF-visible table mapping major claims to evidence and boundaries.
- Modify: `reports/final/main.tex`
  Include the claim/evidence/boundary table, keep or update the tier-economics table, and remove the road-show appendix input if it is no longer needed in the report.
- Modify: `reports/final/checklist.md`
  State that a separate three-minute demo video accompanies the submission; avoid claiming the report itself contains road-show evidence.
- Modify: `reports/final/claim_evidence_map.md`
  Mirror the new in-PDF claim/evidence/boundary table and record that road-show evidence is external to the report.
- Modify: `reports/final/build_notes.md`
  Record compile command, page count, section order, and residual risks after this targeted polish.
- Optional keep, but do not expand: `reports/final/appendix/demo_evidence.tex`
  Leave as an artifact if useful, but do not include it in `main.tex` unless the instructor explicitly requests road-show evidence inside the PDF.

## Task 1: Tier-Economics Sensitivity Table

**Files:**
- Modify: `reports/final/tables/tier_economics.tex`
- Modify: `reports/final/results/cost_benefit.md`
- Modify: `reports/final/main.tex` if wording around Section 7 needs a tighter pointer.

- [ ] **Step 1: Replace qualitative tier economics with illustrative sensitivity**

Use the existing Node 9 cost figures already in `reports/final/results/cost_benefit.md`:

- 20-PDF evidence packet API/compute cost: `0.39 USD`.
- 50-PDF consulting/R&D evidence scan API/compute cost: `1.13 USD`.
- These are planning estimates, excluding hosting, support, abuse, licensing, sales, conversion, and retention.

Rewrite `reports/final/tables/tier_economics.tex` as a compact table with rows like:

```tex
\begin{table}[t]
  \caption{Illustrative subscription stress test for managed-LLM access. Costs reuse the Node 9 API/compute estimates and are planning assumptions, not production quotas or validated margins.}
  \label{tab:tier-economics}
  \centering
  \small
  \setlength{\tabcolsep}{3pt}
  \begin{tabularx}{\linewidth}{p{0.14\linewidth}p{0.16\linewidth}p{0.22\linewidth}p{0.18\linewidth}Y}
    \toprule
    Tier & Modeled month & Modeled API cost & Revenue headroom before support & Boundary \\
    \midrule
    Free BYOK & User-supplied model/key. & 0~USD PaperMemory model spend. & 0~USD subscription revenue. & Adoption tier; group/request limits control local load. \\
    10~USD/month & Four 20-PDF evidence-packet runs. & 4 $\times$ 0.39 = 1.56~USD. & 8.44~USD before hosting/support/licensing. & Light-use stress case, not a promised quota; over-cap falls back to BYOK or wait. \\
    20~USD/month & Four 50-PDF evidence-scan runs. & 4 $\times$ 1.13 = 4.52~USD. & 15.48~USD before hosting/support/licensing. & Heavier-use stress case with rate limits and fair-use review. \\
    Heavy-use guard & Eight 50-PDF evidence-scan runs. & 8 $\times$ 1.13 = 9.04~USD. & 10.96~USD at 20~USD price before non-model costs. & Shows why unlimited inference is not offered. \\
    \bottomrule
  \end{tabularx}
\end{table}
```

- [ ] **Step 2: Add a Markdown explanation to `cost_benefit.md`**

Add a subsection after `## Tier Economics Assumption`:

```markdown
### Illustrative Managed-Access Sensitivity

The tier table uses existing Node 9 per-scenario API/compute costs as stress cases. A modeled 10 USD/month light-use month assumes four 20-PDF evidence-packet runs at 0.39 USD each, leaving 8.44 USD before hosting, support, licensing, abuse monitoring, and payment costs. A modeled 20 USD/month heavier-use month assumes four 50-PDF evidence-scan runs at 1.13 USD each, leaving 15.48 USD before those non-model costs. An eight-run heavy-use guard still leaves 10.96 USD before non-model costs at the 20 USD price, but it shows why the product must use weekly caps, rate limits, BYOK fallback, or add-ons instead of unlimited inference.

These rows are illustrative stress cases, not production quotas, validated margins, or customer usage telemetry.
```

- [ ] **Step 3: Tighten Section 7 prose if needed**

Make sure `reports/final/main.tex` describes the table as an illustrative stress test and not as validated margin.

- [ ] **Step 4: Acceptance check**

Run:

```powershell
rg -n "1\\.56|4\\.52|9\\.04|8\\.44|15\\.48|10\\.96|unlimited|validated margins|production quotas|BYOK|weekly" reports/final/main.tex reports/final/tables/tier_economics.tex reports/final/results/cost_benefit.md
```

Expected: the numeric stress cases appear, and any `unlimited`, `validated margins`, or `production quotas` text appears only as a negative boundary.

## Task 2: In-PDF Claim / Evidence / Boundary Table

**Files:**
- Create: `reports/final/tables/claim_evidence_boundary.tex`
- Modify: `reports/final/main.tex`
- Modify: `reports/final/claim_evidence_map.md`

- [ ] **Step 1: Create the compact table**

Create `reports/final/tables/claim_evidence_boundary.tex`:

```tex
\begin{table}[t]
  \caption{Major claims, evidence, and boundaries visible to graders inside the PDF.}
  \label{tab:claim-evidence-boundary}
  \centering
  \small
  \setlength{\tabcolsep}{3pt}
  \begin{tabularx}{\linewidth}{p{0.22\linewidth}YY}
    \toprule
    Claim & Evidence in this report & Boundary \\
    \midrule
    Postgraduate researchers show early willingness to test/pay. & Interview aggregate: 10 postgraduate researchers, 4.2/5 conditional purchase likelihood, 70\% managed-access preference. & Convenience sample; not product-market fit, paid conversion, retention, or validated revenue. \\
    PaperMemory is a compound AI system rather than a chat-only UI. & EvidencePackets, visual and text retrieval paths, BM25, hybrid page fusion, bounded evidence loop, reliability status, and evidence-visible UI. & Bounded local agent; not general AGI or full literature-review automation. \\
    Retrieval components work on the local fixture suite. & Keyword, visual API, BM25, and hybrid rows; BM25 reaches 88.9\% R@1 and 100.0\% retrieval-level refusal correctness on the synthetic fixture. & Synthetic/local fixture; not real-corpus superiority. \\
    Subscription packaging has bounded cost logic. & Node 9 cost stress test plus managed-access tier sensitivity. & Planning estimate; excludes hosting, support, licensing, conversion, retention, and usage telemetry. \\
    Trust behavior is implemented as visible limits. & Robustness matrix, failure gallery, reliability labels, citation filtering, and prompt-injection-like PDF text boundary. & Deterministic regression evidence; not comprehensive security or OCR robustness. \\
    \bottomrule
  \end{tabularx}
\end{table}
```

- [ ] **Step 2: Include the table in `main.tex`**

Preferred placement: after `\input{tables/market_validation}` in the Introduction, because it turns the report's story into a grader-facing evidence map early.

If the Introduction becomes too dense, move it to the start of `Limitations, Ethics, and Reproducibility`.

Add:

```tex
\input{tables/claim_evidence_boundary}
```

- [ ] **Step 3: Mirror in `claim_evidence_map.md`**

Add a top subsection:

```markdown
## PDF-Visible Summary Table

The report now includes `reports/final/tables/claim_evidence_boundary.tex`, a compact in-PDF table with five major claims: market signal, compound AI architecture, synthetic retrieval results, bounded subscription cost logic, and trust behavior. The table intentionally pairs each claim with a boundary so graders can see what the report does and does not claim without opening this external map.
```

- [ ] **Step 4: Acceptance check**

Run:

```powershell
rg -n "claim_evidence_boundary|claim-evidence-boundary|product-market fit|real-corpus superiority|validated revenue|comprehensive security" reports/final/main.tex reports/final/tables/claim_evidence_boundary.tex reports/final/claim_evidence_map.md
```

Expected: table is included and risky phrases appear only as boundaries.

## Task 3: Road-Show Scope Reduction

**Files:**
- Modify: `reports/final/main.tex`
- Modify: `reports/final/checklist.md`
- Modify: `reports/final/build_notes.md`
- Leave unchanged unless needed: `reports/final/appendix/demo_evidence.tex`, `demo/script.md`, `demo/shot-list.md`, `demo/final-video-notes.md`

- [ ] **Step 1: Remove road-show appendix from the PDF**

In `reports/final/main.tex`, remove or comment out:

```tex
\input{appendix/demo_evidence}
```

Rationale: the team will submit a separate demo video, so the report should not spend appendix space proving road-show readiness.

- [ ] **Step 2: Replace report-facing road-show wording**

If `main.tex` says the appendix maps road-show scenes to artifacts, replace that sentence with:

```tex
A separate three-minute demo video accompanies the submission; the report focuses on technical evidence, market proof, cost stress testing, and reproducibility.
```

- [ ] **Step 3: Update `checklist.md`**

Add or replace road-show language:

```markdown
- Road show: a separate three-minute demo video accompanies the submission. The PDF does not duplicate the video storyboard except for reproducibility and claim-boundary notes.
```

- [ ] **Step 4: Acceptance check**

Run:

```powershell
rg -n "demo_evidence|Road-Show Evidence Map|separate three-minute demo|recorder-ready|completed video" reports/final/main.tex reports/final/checklist.md reports/final/build_notes.md
```

Expected: `main.tex` does not include `appendix/demo_evidence`; any road-show wording says the video is separate and does not claim a missing file inside the report.

## Task 4: Final Compile and QA

**Files:**
- Modify: `reports/final/build_notes.md`

- [ ] **Step 1: Compile PDF**

Run:

```powershell
python "C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\0.2.2\scripts\compile_latex.py" D:\codex\papermemory\reports\final\main.tex --json
```

Expected: exit status 0 and `reports/final/main.pdf` updated.

- [ ] **Step 2: Check page count and order**

Run:

```powershell
python -c "from pypdf import PdfReader; r=PdfReader('reports/final/main.pdf'); print('pages=' + str(len(r.pages))); keys=['References','Reproducibility Commands','Interview Market Validation','Full Metric Tables','Robustness Failure Gallery','NeurIPS Paper Checklist']; [print(k + '=' + str(next((i+1 for i,p in enumerate(r.pages) if k in (p.extract_text() or '')), 'not found'))) for k in keys]"
```

Expected: main body remains nine pages or fewer before references; references, appendix, and checklist remain in the expected order.

- [ ] **Step 3: Placeholder and overclaim scan**

Run:

```powershell
rg -n "TODO|TBD|FIXME|\?\?|placeholder|unlimited inference|product-market fit|paid conversion|retention|validated revenue|real-corpus superiority|comprehensive security|OCR robustness|dense semantic retrieval" reports/final/main.tex reports/final/appendix reports/final/tables reports/final/results reports/final/checklist.md reports/final/claim_evidence_map.md demo
```

Expected: no placeholders; risky phrases appear only in explicit limitation or boundary statements.

- [ ] **Step 4: Citation key check**

Run:

```powershell
$text = Get-Content -LiteralPath 'reports\final\main.tex' -Raw
$cites = [regex]::Matches($text, '\\citep\{([^}]*)\}') | ForEach-Object { $_.Groups[1].Value.Split(',') } | ForEach-Object { $_.Trim() } | Sort-Object -Unique
$items = [regex]::Matches($text, '\\bibitem(?:\[[^]]*\])?\{([^}]*)\}') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$missing = $cites | Where-Object { $items -notcontains $_ }
if ($missing) { $missing } else { 'all cite keys resolved' }
```

Expected: `all cite keys resolved`.

- [ ] **Step 5: Whitespace check**

Run:

```powershell
git diff --check -- reports/final docs/superpowers/plans .planning/2026-06-28-paper-memory-final-report-evidence-tightening
```

Expected: exit status 0.

- [ ] **Step 6: Update build notes**

Append a 2026-06-28 entry to `reports/final/build_notes.md` with:

- tier-economics sensitivity table added;
- claim/evidence/boundary table added;
- road-show appendix removed or de-emphasized because separate video accompanies the submission;
- compile command and result;
- final page count and section order;
- residual risks.

## Execution Strategy

Recommended execution mode: inline execution in this session, because all edits are tightly coupled report files and the next tasks are small. If subagents are used, use at most one subagent at a time and let the main agent review before proceeding.

Fastest path:

1. Implement Task 1 manually.
2. Implement Task 2 manually.
3. Implement Task 3 manually.
4. Compile and run QA from Task 4.

## Acceptance Criteria

- `reports/final/tables/tier_economics.tex` contains numeric illustrative sensitivity derived from existing Node 9 costs, with explicit non-production caveats.
- `reports/final/tables/claim_evidence_boundary.tex` exists and is included in `main.tex`.
- `main.tex` no longer spends appendix space on road-show evidence mapping unless the user reverses this decision.
- `reports/final/checklist.md` says a separate three-minute demo video accompanies the submission.
- No new interview facts, participant rows, direct quotes, paid conversion claims, or validated margin claims are introduced.
- `reports/final/main.pdf` compiles successfully and the main body remains within the page limit.
