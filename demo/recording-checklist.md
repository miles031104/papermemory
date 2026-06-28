# PaperMemory Demo Recording Checklist

Use this checklist to record the three-minute demo from the Node 11 script. It assumes the package is being recorded from `D:\codex\llm_paper_assis\papermemory`.

## 1. Local Server Startup

1. Open PowerShell at the repository root.
2. Confirm the branch and working state:

```powershell
git status --short --branch
python --version
node --version
npm --version
```

3. Start the API in Terminal 1:

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

4. Start the web app in Terminal 2:

```powershell
cd apps\web
npm run dev
```

5. Open the app at `http://localhost:3000`. Keep `http://127.0.0.1:3000` as the alternate URL.

## 2. Seeded Corpus And Report Assets

- Preferred live path: use the existing local/synthetic seeded papers from the Node 0-10 workflow and a paper group with ready pages.
- Ask one scoped question that naturally returns more than one page or more than one paper.
- Keep these static fallback files open in editor/PDF viewer tabs:
  - `reports/final/results/chat_ui_packet.md`
  - `reports/final/results/agent_trace_examples.md`
  - `reports/final/results/failure_gallery.md`
  - `reports/final/results/robustness_matrix.md`
  - `reports/final/results/cost_benefit.md`
  - `reports/final/main.pdf`
- Do not change Node 0-10 result values for the demo. If a live seeded corpus is unavailable, record the fallback documents instead of inventing screenshots.

## 3. Provider Key And Model Settings

- BYOK live path: set the local `.env` provider key expected by the API, then use the configured chat model already supported by the app.
- Keep `retrieval_mode` on the scoped hybrid path when demonstrating EvidencePacket provenance.
- No-key fallback path: do not attempt to fake a live model answer. Record `chat_ui_packet.md`, `agent_trace_examples.md`, and `failure_gallery.md` as static proof of the packet, trace, and refusal behavior.
- Avoid narrating provider-specific performance, real-corpus quality, OCR robustness, dense semantic retrieval, guaranteed ROI, or feature parity with Elicit or Consensus.

## 4. Browser And Recording Setup

- Browser: Chrome or Edge.
- Window size: 1920 x 1080 preferred; 1600 x 900 acceptable.
- Browser zoom: 90% for dashboard/chat recording; 100% for PDF/report pages if text remains readable.
- Recording canvas: 1080p, 30 fps.
- Cursor: visible, with slow deliberate clicks on citation chips, evidence cards, trace rows, and report tables.
- Audio: external mic if available; record a 10-second test clip and listen before the final take.
- Captions or overlays: avoid adding in-video feature explanations. The narration should explain the visible screen moments.

## 5. Backup Capture Notes

- Capture a short backup clip of each required screen moment before recording the full take.
- If the live UI fails, record static fallback assets in this order: script title or report title, `chat_ui_packet.md`, `agent_trace_examples.md`, `failure_gallery.md`, `cost_benefit.md`, and `main.pdf`.
- If the evidence panel is slow to populate, pause recording and use the early evidence frame notes in `chat_ui_packet.md`.
- If report PDF rendering is unavailable, use `reports/final/main.tex` title and the Markdown result files, but say the package includes `reports/final/main.pdf` only if the PDF file exists.
