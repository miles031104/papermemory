# Final Report Build Notes

Date: 2026-06-28

## Package Summary

The current final report package under `reports/final/` includes the fast report patch plus the 2026-06-28 evidence-tightening pass:

- Formatting: NeurIPS style, compiled single PDF, main body within the nine-page limit.
- Technical Depth: executable same-fixture keyword baseline appears before BM25, visual, and hybrid rows.
- Market Proof: aggregate-only interview questionnaire protocol uses only `n=10`, `4.2/5`, and `70%`.
- Profit Logic: tier economics now include illustrative provider-compliant API relay sensitivity using 10-PDF and 30-PDF Node 9 API/compute costs.
- Claim Evidence: an in-PDF claim/evidence table appears near the start of the paper.
- Road Show: a separate three-minute demo video accompanies the submission; the PDF no longer spends appendix space on road-show scene mapping.

New or updated report-facing repair assets include:

- `reports/final/tables/claim_evidence_boundary.tex`
- `reports/final/tables/tier_economics.tex`
- `reports/final/results/cost_benefit.md`
- `reports/final/claim_evidence_map.md`
- `reports/final/checklist.md`
- `reports/final/main.tex`
- `reports/final/main.pdf`

## Compile Command

```powershell
python "C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\0.2.2\scripts\compile_latex.py" D:\codex\papermemory\reports\final\main.tex --json
```

Final compile result:

- Compiler: bundled Tectonic 0.16.9.
- Exit status: 0.
- PDF: `reports/final/main.pdf`.
- Total PDF pages: 12.
- Claim/evidence table: page 2.
- References begin: page 8.
- Appendix content begins: page 10.
- Reproducibility Commands: page 10.
- Interview Market Validation: page 10.
- Full Metric Tables: page 11.
- Robustness Failure Gallery: page 11.
- Road-show appendix heading: not found in the PDF.
- Checklist claims item: page 12.
- Main-body estimate: 7 pages before references, within the nine-page main-body limit.
- Warnings: underfull boxes in narrow tables and bibliography/path lines; no overfull warnings appeared in the captured final compile output.

## Baseline Command

```powershell
python eval/retrieval/run_retrieval_eval.py --mode keyword-synthetic --output-prefix keyword-baseline
```

Recorded result:

- Recall@1: 88.9%.
- Recall@3: 100.0%.
- Recall@5: 100.0%.
- Citation-page correctness: 100.0%.
- Retrieval-level refusal correctness: 33.3%.
- Output artifacts: `keyword-baseline.json`, `keyword-baseline.csv`, `keyword-baseline.md`, and `reports/final/results/keyword_baseline_metrics.md`.

## QA Results

Citation-key check:

```powershell
$text = Get-Content -LiteralPath 'reports\final\main.tex' -Raw
$cites = [regex]::Matches($text, '\\citep\{([^}]*)\}') | ForEach-Object { $_.Groups[1].Value.Split(',') } | ForEach-Object { $_.Trim() } | Sort-Object -Unique
$items = [regex]::Matches($text, '\\bibitem(?:\[[^]]*\])?\{([^}]*)\}') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$missing = $cites | Where-Object { $items -notcontains $_ }
```

Result: all 16 `\citep{...}` keys resolve to inline bibliography items; the bibliography contains 30 items.

PDF page check:

```powershell
python -c "from pypdf import PdfReader; r=PdfReader('reports/final/main.pdf'); print('pages=' + str(len(r.pages))); keys=['Major report claims and supporting evidence','References','Reproducibility Commands','Interview Market Validation','Full Metric Tables','Robustness Failure Gallery','Claims. [Yes]']; [print(k + '=' + str(next((i+1 for i,p in enumerate(r.pages) if k in (p.extract_text() or '')), 'not found'))) for k in keys]"
```

Result: `pages=12`, `Major report claims and supporting evidence=2`, `References=8`, `Reproducibility Commands=10`, `Interview Market Validation=10`, `Full Metric Tables=11`, `Robustness Failure Gallery=11`, `Claims. [Yes]=12`.

Incomplete-marker scan over report-facing files:

Result: no matches for unfinished-work markers in the PDF source, appendices that are included in the PDF, tables, result summaries, checklist, or claim map.

Road-show stale-wording scan over report-facing files:

Result: no matches for the old appendix input id or old readiness/video-existence phrases. The PDF-facing text says a separate three-minute demo video accompanies the submission, without claiming a verified local video file.

Overclaim scan over report-facing files:

Result: matches are explicit limitation or negative-boundary phrases, not positive claims.

Whitespace check:

```powershell
git diff --check -- reports/final docs/superpowers/plans/2026-06-28-paper-memory-final-report-evidence-tightening.md .planning/2026-06-28-paper-memory-final-report-evidence-tightening .planning/.active_plan
```

Result: exit status 0.

## Remaining Risks

- Evaluation is still synthetic/local and should not be presented as real-corpus performance.
- Interview evidence is aggregate-only from 10 postgraduate researchers. It supports early willingness-to-test, not product-market fit, paid conversion, retention, or validated revenue.
- Tier economics are illustrative planning stress cases. They assume provider-compliant API relay or commercial API access, not account pooling or subscription resale. Exact quotas, support costs, hosting costs, abuse costs, payment costs, conversion, retention, and production margins require telemetry.
- The separate three-minute demo video is a submission artifact outside the PDF; this note does not verify a local video file.
- Cost sources use the 2026-06-24 Node 9 snapshot and should be refreshed before external investor or customer use.
- Production commercialization still needs hosting/support measurement, abuse controls, usage telemetry, and PyMuPDF/MuPDF licensing review.
