# PaperMemory Final Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove final report polish risks flagged by an independent reviewer while preserving the current evidence boundaries and compiled NeurIPS-style PDF.

**Architecture:** This is a report-facing LaTeX polish pass, not a system redesign. The edits should make the PDF read like a finished course report by removing internal node/process language, making the compound AI system components explicit, clarifying the companion road-show video, and reducing local path noise in appendices.

**Tech Stack:** LaTeX with `neurips_2025.sty`, Tectonic via the bundled LaTeX helper, PowerShell, `rg`, `pypdf`, and existing report sources under `reports/final/`.

---

## Scope And File Map

Modify only report-facing source files that affect `reports/final/main.pdf`:

- Modify: `reports/final/main.tex`
  - Remove internal `Node 9` / `Node 10` wording from main text and references.
  - Add one explicit compound-stack sentence in the architecture section.
  - Clarify the three-minute road-show video sentence without claiming the video is embedded in the PDF.
- Modify: `reports/final/tables/cost_summary.tex`
  - Rename the caption from internal node language to report-facing cost-stress-test language.
- Modify: `reports/final/tables/claim_evidence_boundary.tex`
  - Remove `Node 9` from the cost evidence row.
- Modify: `reports/final/appendix/reproducibility.tex`
  - Replace local absolute paths and personal helper command with repo-relative wording and a generic compile command.
- Modify: `reports/final/appendix/robustness_cost.tex`
  - Rename the `Node 9` formula reference to `stress-test formula`.
- Regenerate: `reports/final/main.pdf`

Do not rewrite result artifacts such as `reports/final/results/*.md` unless a report-facing appendix includes their text directly. Those files are local audit artifacts and may retain historical node labels without appearing in the PDF.

---

### Task 1: Remove Internal Node Language From Report-Facing Text

**Files:**
- Modify: `reports/final/main.tex`
- Modify: `reports/final/tables/cost_summary.tex`
- Modify: `reports/final/tables/claim_evidence_boundary.tex`
- Modify: `reports/final/appendix/robustness_cost.tex`

- [ ] **Step 1: Replace main-text `Node 9` cost wording**

In `reports/final/main.tex`, replace:

```tex
The cost model supports a plausible subscription experiment under bounded usage. The Node 9 stress test estimates API/compute costs of \$0.19 for a 10-PDF evidence packet, \$0.68 for a 30-PDF project evidence scan, and \$1.62 for systematic-review pre-screening, with positive base-case net savings in all three scenarios after operation, verification, API/compute, and scenario license assumptions.
```

with:

```tex
The cost model supports a plausible subscription experiment under bounded usage. The cost stress test estimates API/compute costs of \$0.19 for a 10-PDF evidence packet, \$0.68 for a 30-PDF project evidence scan, and \$1.62 for systematic-review pre-screening, with positive base-case net savings in all three scenarios after operation, verification, API/compute, and scenario license assumptions.
```

- [ ] **Step 2: Replace the cost formula lead-in**

In `reports/final/main.tex`, replace:

```tex
The commercial question is whether evidence-packet work can save enough expert time to justify a paid workflow while keeping human verification in place. Node 9 models that question with:
```

with:

```tex
The commercial question is whether evidence-packet work can save enough expert time to justify a paid workflow while keeping human verification in place. The stress test models that question with:
```

- [ ] **Step 3: Replace tier-economics `Node 9` wording**

In `reports/final/main.tex`, replace:

```tex
The interview signal supports a subscription experiment rather than a BYOK-only product. Seven of 10 interviewed postgraduate researchers preferred PaperMemory-provided API/model access through a monthly subscription. Table~\ref{tab:tier-economics} uses the 10-PDF and 30-PDF Node 9 API/compute estimates as illustrative managed-access stress cases, not production quotas or validated margins.
```

with:

```tex
The interview signal supports a subscription experiment rather than a BYOK-only product. Seven of 10 interviewed postgraduate researchers preferred PaperMemory-provided API/model access through a monthly subscription. Table~\ref{tab:tier-economics} uses the 10-PDF and 30-PDF cost-stress-test estimates as illustrative managed-access cases, not production quotas or validated margins.
```

- [ ] **Step 4: Replace internal source labels in References**

In `reports/final/main.tex`, make these exact replacements:

```text
source checked for Node 10 -> source checked for this report
Node 9 source snapshot 2026-06-24 -> source snapshot 2026-06-24
Node 9 market-context snapshot 2026-06-24 -> market-context snapshot 2026-06-24
```

Expected remaining internal labels after this step:

```powershell
rg -n "Node [0-9]|source checked for Node|market-context snapshot" reports/final/main.tex
```

Expected output: no `Node` or `source checked for Node` matches; `market-context snapshot` may remain without `Node`.

- [ ] **Step 5: Update report table captions/evidence labels**

In `reports/final/tables/cost_summary.tex`, replace the caption:

```tex
\caption{Node 9 planning estimates under stated assumptions. API/compute cost is per scenario, and savings are net USD after operation, human verification, API/compute, and license assumptions.}
```

with:

```tex
\caption{Cost stress-test estimates under stated assumptions. API/compute cost is per scenario, and savings are net USD after operation, human verification, API/compute, and license assumptions.}
```

In `reports/final/tables/claim_evidence_boundary.tex`, replace:

```tex
Node 9 10-PDF/30-PDF cost stress test plus provider-compliant API relay sensitivity.
```

with:

```tex
10-PDF/30-PDF cost stress test plus provider-compliant API relay sensitivity.
```

In `reports/final/appendix/robustness_cost.tex`, replace:

```tex
The cost model uses the Node 9 formula:
```

with:

```tex
The cost model uses the stress-test formula:
```

- [ ] **Step 6: Verify internal language cleanup**

Run:

```powershell
rg -n "Node [0-9]|source checked for Node|Node 9|Node 10" reports/final/main.tex reports/final/appendix reports/final/tables
```

Expected: no output. If matches appear only in uncompiled files such as `appendix/demo_evidence.tex`, decide whether the file is included in `main.tex`; if it is not included, do not expand scope unless the wording is report-facing.

---

### Task 2: Make Compound AI Components Explicit

**Files:**
- Modify: `reports/final/main.tex`

- [ ] **Step 1: Add explicit compound-stack sentence**

In `reports/final/main.tex`, find the opening paragraph of `\section{Compound AI System Architecture}`:

```tex
PaperMemory is a compound AI system over a local PDF collection. The ingestion path renders PDFs into page artifacts and extracts selectable text where the PDF permits it. Each page can therefore carry an image, a caption or text snippet, a selectable-text manifest entry, and a quality label such as low-text or OCR-needed. This split matters because visual retrieval can still use page layout, while BM25 can use exact terms when text exists.
```

Replace it with:

```tex
PaperMemory is a compound AI system over a local PDF collection. The implemented stack combines a Qdrant-compatible page-vector store, VisRAG-style page-image retrieval, a BM25 text-manifest index, provider LLM generation through BYOK or managed API relay, server-side EvidencePacket validation, a reliability verifier, and an evidence-visible UI. The ingestion path renders PDFs into page artifacts and extracts selectable text where the PDF permits it. Each page can therefore carry an image, a caption or text snippet, a selectable-text manifest entry, and a quality label such as low-text or OCR-needed. This split matters because visual retrieval can still use page layout, while BM25 can use exact terms when text exists.
```

- [ ] **Step 2: Verify compound terms are visible**

Run:

```powershell
rg -n "Qdrant-compatible|VisRAG-style|BM25 text-manifest|provider LLM generation|reliability verifier|evidence-visible UI" reports/final/main.tex
```

Expected: one match in the architecture section.

---

### Task 3: Clarify Road-Show Video Coverage

**Files:**
- Modify: `reports/final/main.tex`

- [ ] **Step 1: Replace generic video sentence**

In `reports/final/main.tex`, replace the final sentence of the reproducibility paragraph:

```tex
A separate three-minute demo video accompanies the submission; the report focuses on technical evidence, market proof, cost stress testing, and reproducibility.
```

with:

```tex
A separate three-minute road-show video accompanies the submission and shows the investor-facing flow: PDF upload, evidence retrieval, a reliability warning for unsupported claims, and the subscription value proposition; the report focuses on technical evidence, market proof, cost stress testing, and reproducibility.
```

- [ ] **Step 2: Verify the report does not overclaim embedded video evidence**

Run:

```powershell
rg -n "road-show|three-minute|completed video|recorder-ready|accompanies the submission" reports/final/main.tex reports/final/appendix
```

Expected:
- `main.tex` says the separate road-show video accompanies the submission and describes what it shows.
- No included appendix claims the PDF itself contains the video.

---

### Task 4: Remove Local Machine Path Noise From Appendix A

**Files:**
- Modify: `reports/final/appendix/reproducibility.tex`

- [ ] **Step 1: Replace absolute local root/junction paragraph**

In `reports/final/appendix/reproducibility.tex`, replace:

```tex
The active repository root is \artifact{D:/codex/papermemory}. The older \artifact{D:/codex/llm\_paper\_assis/papermemory} path is now a junction to this working tree. The recorded environment for the final package is branch \artifact{codex/papermemory-evidence-agent}, baseline commit \artifact{6884d738df9d685bad4f5a673a7d13a7bc2fb691}, Python 3.12.7, Node.js v22.18.0, and npm 10.9.3.
```

with:

```tex
The report package is built from the PaperMemory repository root. The recorded environment for the final package is branch \artifact{codex/papermemory-evidence-agent}, baseline commit \artifact{6884d738df9d685bad4f5a673a7d13a7bc2fb691}, Python 3.12.7, Node.js v22.18.0, and npm 10.9.3.
```

- [ ] **Step 2: Replace personal LaTeX helper command**

In `reports/final/appendix/reproducibility.tex`, replace the current verbatim block:

```tex
\begin{verbatim}
python "C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\
0.2.2\scripts\compile_latex.py" D:\codex\papermemory\
reports\final\main.tex --json
\end{verbatim}
```

with:

```tex
\begin{verbatim}
cd reports/final
tectonic -X compile --outdir . --outfmt pdf --untrusted main.tex
\end{verbatim}
```

- [ ] **Step 3: Replace reproducibility paragraph in main text**

In `reports/final/main.tex`, replace:

```tex
Reproducibility materials live under the active repository root \artifact{D:/codex/papermemory}. The older \artifact{D:/codex/llm\_paper\_assis/papermemory} path is now a junction to the same working tree. Appendix~\ref{app:reproducibility} records the branch, baseline environment, LaTeX command, and verification snapshots.
```

with:

```tex
Reproducibility materials live under the PaperMemory repository root. Appendix~\ref{app:reproducibility} records the branch, baseline environment, LaTeX command, and verification snapshots.
```

- [ ] **Step 4: Verify local path cleanup**

Run:

```powershell
rg -n "D:/codex|C:\\\\Users|junction|llm\\_paper\\_assis|Miles CUI" reports/final/main.tex reports/final/appendix reports/final/tables
```

Expected: no output from report-facing sources.

---

### Task 5: Final Compile And Format Verification

**Files:**
- Regenerate: `reports/final/main.pdf`

- [ ] **Step 1: Compile the PDF**

Run:

```powershell
python "C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\0.2.2\scripts\compile_latex.py" "D:\codex\papermemory\reports\final\main.tex" --compiler tectonic
```

Expected:

```text
Exit code: 0
PDF: D:\codex\papermemory\reports\final\main.pdf
```

- [ ] **Step 2: Check citations, references, and overfull boxes**

Run:

```powershell
$out = Join-Path $env:TEMP ('papermemory-tex-log-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $out | Out-Null
& "C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\0.2.2\bin\tectonic.exe" -X compile --outdir $out --outfmt pdf --keep-logs --untrusted main.tex | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
rg -n "undefined|Undefined|Citation.*undefined|Reference.*undefined|There were undefined|Overfull" (Join-Path $out 'main.log')
```

Workdir: `D:\codex\papermemory\reports\final`

Expected: `rg` exits with code 1 because no undefined citations/references or overfull boxes are found.

- [ ] **Step 3: Check PDF page order and self-reference cleanup**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "from pypdf import PdfReader; r=PdfReader('reports/final/main.pdf'); pages=[(p.extract_text() or '').replace('ﬁ','fi').replace('ﬂ','fl') for p in r.pages]; text='\n'.join(pages); print('pages='+str(len(r.pages))); print('references_page='+str(next((i+1 for i,p in enumerate(pages) if 'References' in p), 'not found'))); print('appendix_page='+str(next((i+1 for i,p in enumerate(pages) if 'A Reproducibility Commands and Environment' in p), 'not found'))); print('checklist_page='+str(next((i+1 for i,p in enumerate(pages) if 'Claims.' in p and 'Limitations.' in p and 'Licenses and assets.' in p), 'not found'))); print('self_refs='+str(('PaperMemory(2026' in text) or ('PaperMemory local artifact' in text) or ('paperMemory' in text))); print('compound_stack='+str('Qdrant-compatible page-vector store' in text)); print('roadshow='+str('PDF upload, evidence retrieval' in text));"
```

Expected:

```text
pages=12
references_page=8
appendix_page=9
checklist_page=12
self_refs=False
compound_stack=True
roadshow=True
```

- [ ] **Step 4: Check NeurIPS style hash against `Styles.zip`**

Run:

```powershell
$tmp = Join-Path $env:TEMP ('neurips-style-check-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
tar -xf 'D:\Download\Styles.zip' -C $tmp
$repo=(Get-FileHash -Algorithm SHA256 'reports/final/neurips_2025.sty').Hash
$zip=(Get-FileHash -Algorithm SHA256 (Join-Path $tmp 'Styles\neurips_2025.sty')).Hash
Write-Output "repo_sty_sha256=$repo"
Write-Output "zip_sty_sha256=$zip"
if ($repo -ne $zip) { exit 1 }
```

Expected: both hashes are identical.

- [ ] **Step 5: Check diff hygiene**

Run:

```powershell
git diff --check -- reports/final/main.tex reports/final/tables/cost_summary.tex reports/final/tables/claim_evidence_boundary.tex reports/final/appendix/reproducibility.tex reports/final/appendix/robustness_cost.tex reports/final/main.pdf
```

Expected: exit code 0. Git may print CRLF warnings; those are acceptable if there are no whitespace-error lines.

---

## Self-Review Checklist

- [ ] The plan removes internal node/process wording from all report-facing sources, including main text, references, included tables, and included appendices.
- [ ] The plan explicitly names compound AI components without claiming a new unimplemented subsystem.
- [ ] The plan clarifies the road-show video without pretending the PDF contains or proves the video.
- [ ] The plan removes personal machine paths from included report sources while preserving enough reproducibility detail.
- [ ] The final verification checks compile success, page order, self-reference cleanup, NeurIPS style hash, and diff hygiene.

## Expected Outcome

After implementation, the report should address the independent reviewer’s fastest/highest-yield concerns and plausibly improve presentation from roughly `34/40` toward the `36-38/40` range without broadening experiments or inventing additional market evidence.
