# PaperMemory Fast Report Patch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quickly remove the most obvious grading objections in the final PaperMemory report by adding auditable interview evidence, a minimal executable baseline, subscription tier economics, and road-show evidence mapping without expanding into a full real-corpus benchmark.

**Architecture:** This is a report-evidence patch, not a system redesign. The implementation should add small, auditable artifacts under `reports/final/` and `demo/`, run one minimal same-fixture baseline under `eval/retrieval/`, integrate the new evidence into `main.tex`, then recompile and rescan the PDF.

**Tech Stack:** LaTeX, Markdown evidence artifacts, Python retrieval evaluation script, existing synthetic golden questions, bundled Tectonic LaTeX compile helper, `pypdf` PDF checks, PowerShell verification.

---

## Scope Boundary

This plan optimizes for the fastest report-quality gain.

Do:

- Use only the user-provided interview aggregate facts: `n=10`, mean conditional purchase likelihood `4.2/5`, and `70%` preference for PaperMemory-provided API/model access through subscription.
- Add a questionnaire/protocol appendix and aggregate response categories.
- Present `$10/month` and `$20/month` as tiers that include PaperMemory-provided LLM model access support with weekly usage limits.
- Build a minimal same-fixture baseline so the report no longer depends on a qualitative `N/A` baseline row.
- Preserve the current honest boundaries around synthetic/local evaluation and early market evidence.

Do not:

- Invent per-participant raw data, exact interview quotes, or paid conversion.
- Claim product-market fit, real-corpus superiority, OCR robustness, dense semantic retrieval, or production margins.
- Start a 20-50 PDF benchmark unless the user explicitly chooses a slower second phase.

## File Map

- Modify: `reports/final/main.tex`
  Integrate revised market proof, baseline comparison, tier economics, and road-show evidence references.
- Modify: `reports/final/appendix/interview_validation.tex`
  Add questionnaire protocol, aggregate-only response evidence, and limitations.
- Modify: `reports/final/results/interview_market_validation.md`
  Mirror the appendix with questionnaire wording and aggregate-only evidence.
- Modify: `reports/final/tables/market_validation.tex`
  Add a compact line showing protocol/auditability if page budget allows.
- Modify: `eval/retrieval/run_retrieval_eval.py`
  Add a minimal same-fixture baseline mode, named `keyword-synthetic`, using simple token overlap over synthetic page titles/captions.
- Create: `eval/retrieval/results/keyword-baseline.json`
  Generated baseline output.
- Create: `eval/retrieval/results/keyword-baseline.csv`
  Generated baseline per-question output.
- Create: `eval/retrieval/results/keyword-baseline.md`
  Generated readable baseline summary.
- Create: `reports/final/results/keyword_baseline_metrics.md`
  Report-facing metrics summary for the minimal baseline.
- Modify: `reports/final/tables/retrieval_summary.tex`
  Replace the `GPT-only / manual narrative` `N/A` row with the executable keyword baseline row, while optionally mentioning GPT-only as qualitative related context in prose.
- Modify: `reports/final/appendix/full_metrics.tex`
  Add the keyword baseline row and command.
- Modify: `reports/final/results/cost_benefit.md`
  Add tier economics assumptions for weekly usage caps.
- Create: `reports/final/tables/tier_economics.tex`
  Compact table with free BYOK, `$10/month`, `$20/month`, weekly limits, included model support, and margin boundary.
- Modify: `reports/final/tables/pricing_tiers.tex`
  Replace vague quota wording with weekly usage-limit language.
- Modify: `reports/final/appendix/robustness_cost.tex`
  Add cost/tier assumptions and heavy-user caveat.
- Create: `reports/final/appendix/demo_evidence.tex`
  Map road-show scenes to implemented artifacts and fallback evidence.
- Modify: `reports/final/main.tex`
  Include `appendix/demo_evidence` and reference the new evidence in Section 8 or checklist.
- Modify: `reports/final/checklist.md`
  Update reproducibility, market proof, road-show, and dataset rows.
- Modify: `reports/final/claim_evidence_map.md`
  Add rows for questionnaire protocol, keyword baseline, weekly usage limits, and demo evidence mapping.
- Modify: `reports/final/build_notes.md`
  Record commands, output paths, page count, and residual risks.

## Task 1: Interview Appendix And Market Evidence

**Files:**
- Modify: `reports/final/appendix/interview_validation.tex`
- Modify: `reports/final/results/interview_market_validation.md`
- Modify: `reports/final/tables/market_validation.tex`
- Later integration: `reports/final/main.tex`

- [ ] **Step 1: Add an aggregate-only questionnaire protocol to the appendix**

Append these questionnaire items in `reports/final/appendix/interview_validation.tex`:

```tex
\paragraph{Questionnaire protocol.}
The team used a short semi-structured questionnaire. The questions were:
\begin{enumerate}
  \item What is your research stage and how often do you read academic PDFs?
  \item What current tools or workflow do you use for literature reading and citation checking?
  \item If PaperMemory delivered local PDF ingestion, evidence-backed answers, visible page citations, bounded uncertainty, and a smoother model-access path, how likely would you be to pay for it on a 1--5 scale?
  \item Would you prefer bringing your own API key/local model, or using PaperMemory-provided LLM model access through subscription?
  \item Which packaging sounds most acceptable: free BYOK with limited groups, 10~USD/month with weekly managed-model limits, or 20~USD/month with higher weekly managed-model limits?
  \item What risk would stop you from relying on the tool for research writing?
\end{enumerate}
Only aggregate notes are used in this report; the paper does not claim participant-level raw data or paid conversion.
```

- [ ] **Step 2: Add an aggregate response interpretation paragraph**

Use only these facts:

```tex
\paragraph{Aggregate responses.}
Across 10 postgraduate interviewees, the mean conditional purchase likelihood was 4.2/5 if the described workflow was delivered. Seven of the 10 interviewees preferred PaperMemory-provided API/model access through subscription rather than a BYOK-only setup. The report uses this as a willingness-to-test signal for managed LLM access, not as evidence of product-market fit, retention, or paid conversion.
```

- [ ] **Step 3: Mirror the protocol in `interview_market_validation.md`**

Add the same questionnaire list and aggregate-only boundary in Markdown.

- [ ] **Step 4: Update the main-text market paragraph**

In `reports/final/main.tex`, change the interview sentence so it says the appendix records the short questionnaire protocol and aggregate response categories.

- [ ] **Step 5: Acceptance check**

Run:

```powershell
rg -n "participant-level|raw data|paid conversion|product-market fit|4.2|70\\%" reports/final/appendix/interview_validation.tex reports/final/results/interview_market_validation.md reports/final/main.tex
```

Expected: the files mention aggregate evidence and explicitly avoid raw participant or paid-conversion claims.

## Task 2: Minimal Same-Fixture Keyword Baseline

**Files:**
- Modify: `eval/retrieval/run_retrieval_eval.py`
- Create: `eval/retrieval/results/keyword-baseline.json`
- Create: `eval/retrieval/results/keyword-baseline.csv`
- Create: `eval/retrieval/results/keyword-baseline.md`
- Create: `reports/final/results/keyword_baseline_metrics.md`
- Modify: `reports/final/tables/retrieval_summary.tex`
- Modify: `reports/final/appendix/full_metrics.tex`
- Modify: `reports/final/main.tex`

- [ ] **Step 1: Add `keyword-synthetic` as a parser mode**

In `parse_args()`, extend choices:

```python
choices=["synthetic", "keyword-synthetic", "bm25-synthetic", "hybrid-synthetic"]
```

and update the help string to describe keyword overlap as the minimal same-fixture baseline.

- [ ] **Step 2: Implement simple token-overlap scoring**

Add a function that scores each synthetic page by overlap between question tokens and page title/caption tokens. Filter by `paper_ids`; return no pages when `paper_ids` is empty or the best score is zero.

```python
def evaluate_keyword_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages = synthetic_pages()
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        allowed = {str(item) for item in row["paper_ids"]}
        query_tokens = set(TOKEN_RE.findall(row["question"].lower()))
        scored: list[tuple[int, str, int, SyntheticPage]] = []
        if allowed:
            for page in pages:
                if page.paper_id not in allowed:
                    continue
                page_tokens = set(TOKEN_RE.findall(f"{page.title} {page.caption}".lower()))
                score = len(query_tokens.intersection(page_tokens))
                if score > 0:
                    scored.append((-score, page.paper_id, page.page_number, page))
        scored.sort()
        evidence_pages = [(item[3].paper_id, item[3].page_number) for item in scored[:5]]
        expected_pages = {page_key(item) for item in row["expected_pages"]}
        must_cite_pages = {page_key(item) for item in row["must_cite_pages"]}
        should_refuse = bool(row["should_refuse"])
        recall_by_k = {}
        for k in (1, 3, 5):
            top_k_pages = set(evidence_pages[:k])
            recall_by_k[f"recall_at_{k}"] = (
                len(expected_pages.intersection(top_k_pages)) / len(expected_pages)
                if expected_pages
                else None
            )
        evaluated.append(
            {
                "id": row.get("id"),
                "question": row["question"],
                "question_type": row["question_type"],
                "library_id": row.get("library_id"),
                "group_id": row.get("group_id"),
                "provenance": row.get("provenance"),
                "paper_ids": row["paper_ids"],
                "expected_pages": [format_page_key(item) for item in expected_pages],
                "evidence_pages": [format_page_key(item) for item in evidence_pages],
                "recall_at_1": recall_by_k["recall_at_1"],
                "recall_at_3": recall_by_k["recall_at_3"],
                "recall_at_5": recall_by_k["recall_at_5"],
                "citation_page_correct": (
                    must_cite_pages.issubset(set(evidence_pages[:5]))
                    if must_cite_pages and not should_refuse
                    else None
                ),
                "refusal_correct": (len(evidence_pages) == 0) if should_refuse else None,
            }
        )
    return evaluated
```

- [ ] **Step 3: Add keyword output writer**

Add a report writer that mirrors the existing BM25 writer but labels the row:

```text
Keyword overlap baseline
```

Boundary text:

```text
Minimal deterministic same-fixture baseline over synthetic page titles/captions; not an LLM, BM25, VisRAG, or real-corpus benchmark.
```

- [ ] **Step 4: Wire the mode in `main()`**

Before `bm25-synthetic`:

```python
if args.mode == "keyword-synthetic":
    evaluated = evaluate_keyword_rows(rows)
    metrics = aggregate_metrics(evaluated)
    paths = write_keyword_outputs(args.output_prefix, evaluated, metrics)
elif args.mode == "bm25-synthetic":
    ...
```

- [ ] **Step 5: Run the baseline**

Run:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode keyword-synthetic --output-prefix keyword-baseline
```

Expected: JSON, CSV, Markdown, and `reports/final/results/keyword_baseline_metrics.md` are written.

- [ ] **Step 6: Update the retrieval summary table**

Replace the current `GPT-only / manual narrative` row in `reports/final/tables/retrieval_summary.tex` with the measured keyword row. Use the actual metrics from `reports/final/results/keyword_baseline_metrics.md`.

- [ ] **Step 7: Update Section 5 prose**

Change the baseline paragraph so it says:

```text
The first row is a deliberately weak but executable keyword-overlap baseline on the same fixture questions. GPT-only chat and Elicit/Consensus remain qualitative market comparators, not measured baselines.
```

- [ ] **Step 8: Acceptance check**

Run:

```powershell
rg -n "N/A|keyword|GPT-only|qualitative" reports/final/main.tex reports/final/tables/retrieval_summary.tex reports/final/appendix/full_metrics.tex reports/final/results/keyword_baseline_metrics.md
```

Expected: no `N/A` retrieval row remains in the main metric table; GPT-only is described only as qualitative context.

## Task 3: Weekly Usage Limits And Tier Economics

**Files:**
- Modify: `reports/final/results/cost_benefit.md`
- Modify: `reports/final/tables/pricing_tiers.tex`
- Create: `reports/final/tables/tier_economics.tex`
- Modify: `reports/final/appendix/robustness_cost.tex`
- Modify: `reports/final/main.tex`

- [ ] **Step 1: Replace vague quota language in pricing table**

Update `reports/final/tables/pricing_tiers.tex` with explicit weekly-limit wording:

```tex
10~USD/month & PaperMemory-provided LLM model access or API relay for routine postgraduate evidence work. & Weekly managed-model limit for light evidence-packet runs; BYOK fallback after the cap. & User verifies cited pages before using claims in writing. \\
20~USD/month & Higher weekly managed-model limit and larger workspace for heavier literature projects. & Higher weekly cap, rate limits, abuse controls, and support-cost tracking. & User remains responsible for expert judgment and final citation checks. \\
```

- [ ] **Step 2: Create `tier_economics.tex`**

Use a compact table with no invented production telemetry:

```tex
\begin{table}[t]
  \caption{Subscription economics for the proposed managed-LLM tiers. Dollar costs are planning estimates from the Node 9 stress test, not production telemetry.}
  \label{tab:tier-economics}
  \centering
  \small
  \setlength{\tabcolsep}{4pt}
  \begin{tabularx}{\linewidth}{p{0.18\linewidth}YYY}
    \toprule
    Tier & Included access & Weekly boundary & Margin control \\
    \midrule
    Free BYOK & No included PaperMemory model spend. & Limited groups; user supplies key or local model. & PaperMemory avoids variable LLM cost. \\
    10~USD/month & Managed LLM access for light postgraduate use. & Lower weekly evidence-packet cap; BYOK fallback above cap. & Cap keeps expected API cost below subscription revenue under Node 9 base assumptions. \\
    20~USD/month & Managed LLM access for heavier projects. & Higher weekly cap and larger workspace; rate limits for heavy use. & Higher price funds larger model budget, support load, and abuse monitoring. \\
    \bottomrule
  \end{tabularx}
\end{table}
```

- [ ] **Step 3: Include the new table in Section 7**

Add `\input{tables/tier_economics}` after `\input{tables/pricing_tiers}` or replace one table if page budget gets tight.

- [ ] **Step 4: Add a tier-economics paragraph**

In Section 7, write:

```text
The paid tiers bundle LLM access support rather than unlimited inference. The weekly cap is the key margin control: once a user exceeds the managed allowance, the product can pause, ask the user to wait, or fall back to BYOK. This keeps the commercial claim tied to a bounded service design rather than an unlimited API subsidy.
```

- [ ] **Step 5: Update appendix cost assumptions**

In `reports/final/appendix/robustness_cost.tex`, add a paragraph explaining that weekly caps and BYOK fallback are product controls, not validated pricing telemetry.

- [ ] **Step 6: Acceptance check**

Run:

```powershell
rg -n "weekly|cap|BYOK|managed LLM|10~USD|20~USD|unlimited" reports/final/main.tex reports/final/tables/pricing_tiers.tex reports/final/tables/tier_economics.tex reports/final/appendix/robustness_cost.tex
```

Expected: tiers clearly include managed LLM access with weekly caps and do not promise unlimited usage.

## Task 4: Road-Show Evidence Mapping

**Files:**
- Create: `reports/final/appendix/demo_evidence.tex`
- Modify: `reports/final/main.tex`
- Modify: `reports/final/checklist.md`
- Modify: `demo/final-video-notes.md`

- [ ] **Step 1: Create appendix demo evidence map**

Create `reports/final/appendix/demo_evidence.tex`:

```tex
\section{Road-Show Evidence Map}
\label{app:demo-evidence}

The road-show package is recorder-ready rather than a completed video. The report therefore evaluates video readiness through a timed narration script, shot list, fallback assets, and claim-boundary notes.

\begin{table}[h]
  \caption{Three-minute road-show scenes and supporting implementation artifacts.}
  \label{tab:demo-evidence-map}
  \centering
  \small
  \setlength{\tabcolsep}{4pt}
  \begin{tabularx}{\linewidth}{p{0.18\linewidth}YY}
    \toprule
    Scene & Claim shown & Evidence artifact \\
    \midrule
    Problem & Citation and uncertainty are hidden in ordinary PDF chat. & \artifact{demo/script.md}; \artifact{reports/final/claim_evidence_map.md}. \\
    Agent plan & Bounded evidence loop over selected papers. & \artifact{reports/final/results/agent_trace_examples.md}. \\
    EvidencePacket & Accepted citations, evidence ids, page links, limits. & \artifact{reports/final/results/evidence_contract.md}; \artifact{reports/final/results/chat_ui_packet.md}. \\
    Bounded repair & Retry must add accepted evidence or stop. & \artifact{reports/final/results/agent_trace_examples.md}. \\
    Refusal and limits & Missing, conflicting, or unsafe evidence becomes visible limits. & \artifact{reports/final/results/failure_gallery.md}; \artifact{reports/final/results/robustness_matrix.md}. \\
    Cost close & Cost-benefit is a planning stress test, not a guarantee. & \artifact{reports/final/results/cost_benefit.md}; \artifact{demo/final-video-notes.md}. \\
    \bottomrule
  \end{tabularx}
\end{table}
```

- [ ] **Step 2: Include it in `main.tex`**

After `\input{appendix/robustness_cost}`, add:

```tex
\input{appendix/demo_evidence}
```

- [ ] **Step 3: Update road-show checklist**

In `reports/final/checklist.md`, change road-show support from just script alignment to script plus shot list plus appendix evidence map.

- [ ] **Step 4: Acceptance check**

Run:

```powershell
rg -n "Road-Show Evidence|demo_evidence|recorder-ready|completed video|script|shot list" reports/final/main.tex reports/final/appendix/demo_evidence.tex reports/final/checklist.md demo/final-video-notes.md
```

Expected: road-show status is explicit and does not falsely claim a recorded video.

## Task 5: Claim-Evidence Map, Build Notes, Compile, And Final QA

**Files:**
- Modify: `reports/final/claim_evidence_map.md`
- Modify: `reports/final/checklist.md`
- Modify: `reports/final/build_notes.md`
- Modify: `reports/final/main.tex`

- [ ] **Step 1: Update claim-evidence map**

Add rows for:

- Interview questionnaire protocol: supported by `appendix/interview_validation.tex` and `results/interview_market_validation.md`.
- Keyword baseline: supported by `eval/retrieval/results/keyword-baseline.*` and `results/keyword_baseline_metrics.md`.
- Weekly managed-LLM usage limits: supported by `pricing_tiers.tex`, `tier_economics.tex`, and `cost_benefit.md`.
- Road-show evidence map: supported by `appendix/demo_evidence.tex`, `demo/script.md`, and `demo/shot-list.md`.

- [ ] **Step 2: Compile**

Run:

```powershell
python "C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\0.2.2\scripts\compile_latex.py" D:\codex\papermemory\reports\final\main.tex --json
```

Expected: exit status 0 and `reports/final/main.pdf` updated.

- [ ] **Step 3: Page and section order check**

Run:

```powershell
python -c "from pypdf import PdfReader; r=PdfReader('reports/final/main.pdf'); print('pages=' + str(len(r.pages))); keys=['References','Interview Market Validation','Road-Show Evidence Map','NeurIPS Paper Checklist']; [print(k + '=' + str(next((i+1 for i,p in enumerate(r.pages) if k in (p.extract_text() or '')), 'not found'))) for k in keys]"
```

Expected: main body remains under nine pages before references; appendix/checklist order remains acceptable.

- [ ] **Step 4: Placeholder and overclaim scan**

Run:

```powershell
rg -n "TODO|TBD|FIXME|\?\?|placeholder|unlimited|product-market fit|paid conversion|retention|validated revenue|real-corpus superiority|comprehensive security|OCR robustness|dense semantic retrieval" reports/final/main.tex reports/final/appendix reports/final/tables reports/final/results reports/final/checklist.md reports/final/claim_evidence_map.md demo
```

Expected: any matches are explicit negative-boundary phrases, not claims.

- [ ] **Step 5: Whitespace check**

Run:

```powershell
git diff --check -- reports/final eval/retrieval demo docs/superpowers/plans .planning/2026-06-27-paper-memory-fast-report-patch
```

Expected: exit status 0.

- [ ] **Step 6: Update build notes**

Record:

- Keyword baseline command and metrics.
- Interview appendix protocol added with aggregate-only boundary.
- Weekly managed-LLM usage-limit tier economics added.
- Road-show evidence map added.
- Final PDF page count and section order.
- Remaining risks: synthetic fixture evaluation, aggregate-only interview evidence, no completed video unless a real video file is recorded.

## Execution Strategy

Recommended execution mode: inline execution in this session or one worker per task if subagent capacity is available. Because the changes are tightly coupled in `main.tex`, main-agent integration should happen after each worker returns.

Fastest path:

1. Do Task 1 manually.
2. Do Task 2 manually or with one worker, then run the baseline.
3. Do Task 3 manually.
4. Do Task 4 manually.
5. Compile and QA as Task 5.

## Acceptance Criteria

- Main retrieval summary has no `N/A` measured baseline row.
- Interview appendix contains a questionnaire protocol and uses only aggregate facts.
- `$10/month` and `$20/month` tiers explicitly include managed LLM access with weekly usage limits.
- Road-show readiness is backed by an appendix evidence map and does not claim a completed video.
- `main.pdf` compiles with the NeurIPS style and main body remains within the nine-page limit.
- Claim-evidence map and checklist reflect all new evidence.
