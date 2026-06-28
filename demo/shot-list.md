# PaperMemory Demo Shot List

## Final 3-Minute Recording Sequence

This sequence maps each spoken claim in `demo/script.md` to a visible screen moment and a static fallback. Use the live app when available; use the fallback assets when provider keys, seeded papers, or browser state are not ready. Do not claim a recorded final video unless an actual video file is present.

| Time | Spoken claim | Live screen moment | Fallback asset |
| --- | --- | --- | --- |
| 0:00-0:25 | PDF literature work fails when retrieval, citations, and uncertainty are hidden. | Open on the final report title, then move to the PaperMemory chat view with a selected paper group. | `reports/final/main.pdf`; `reports/final/claim_evidence_map.md`. |
| 0:25-0:55 | PaperMemory runs a bounded, server-verified evidence loop over selected papers, not an open-ended literature review. | Ask a scoped hybrid question and show a multi-paper or multi-page answer beginning to stream. | `reports/final/results/chat_ui_packet.md`; `reports/final/results/agent_trace_examples.md`. |
| 0:55-1:25 | The EvidencePacket exposes accepted citations, page evidence, source modality, limits, and page links. | Show the evidence panel, accepted citation chips, `Hybrid` or `BM25 text` modality, packet limits, and click one evidence page/provenance card. | `reports/final/results/evidence_contract.md`; `reports/final/results/chat_ui_packet.md`. |
| 1:25-1:55 | Bounded retrieval repair uses a second pass only when it adds accepted evidence; repeated evidence stops with `no_new_evidence`. | Open the public trace panel or debug trace with pass index, evidence delta count, accepted evidence ids, and stop reason. | `reports/final/results/agent_trace_examples.md`, especially the no-new-evidence trace. |
| 1:55-2:25 | Missing, conflicting, low-text, or prompt-injection-like evidence becomes visible limits, partial answers, or citation stripping. | Show a refusal/partial/limit moment: empty evidence packet, `partial` answer, conflict limit, low-text visual-first limit, or unsupported citation removed. | `reports/final/results/failure_gallery.md`; `reports/final/results/robustness_matrix.md`. |
| 2:25-2:45 | The cost/ROI table is a planning stress test for first-pass evidence gathering and citation packaging with human verification. | Show the cost-benefit table and highlight the base case plus a conservative or negative sensitivity row. | `reports/final/results/cost_benefit.md`; `reports/final/results/cost_benefit.csv`; `reports/final/tables/cost_summary.tex`. |
| 2:45-3:00 | The package is complete for recording, but PaperMemory is not a replacement for expert review or systematic-review workflows. | Close on the final report PDF title page and, if useful, the final-video notes status. | `reports/final/main.pdf`; `demo/final-video-notes.md`. |

## Required Screen Moment Coverage

- Multi-paper or multi-page answer: 0:25-0:55.
- Evidence packet with accepted citations and page evidence: 0:55-1:25.
- Page/evidence click or evidence panel provenance: 0:55-1:25.
- Public bounded trace with pass index, evidence delta, stop reason, or accepted evidence ids: 1:25-1:55.
- Refusal, partial answer, missing evidence, low-text/conflict limit, or citation stripping: 1:55-2:25.
- Cost/ROI table or report page from `cost_benefit.md` or `main.pdf`: 2:25-2:45.
- Final report PDF/title page as closing proof of package completeness: 2:45-3:00.

## Recording Boundaries

- Say "first-pass evidence gathering and citation packaging with human verification," not guaranteed ROI.
- Say "bounded server-verified evidence loop," not autonomous systematic-review replacement.
- Say "deterministic local/synthetic fixtures and regression tests," not real-corpus performance.
- Do not claim comprehensive security, OCR robustness, dense semantic retrieval, validated customer demand, or feature parity with Elicit or Consensus.

## Node 6 Verified Chat/UI Segment

1. Open the chat view with a group that has ready papers.
2. Ask a paper-scoped question and show the backend request uses `retrieval_mode="hybrid"`.
3. Capture the evidence panel populating from the early SSE evidence frame before the final answer completes.
4. Highlight one evidence card with packet-derived source modality, such as `Hybrid`, plus its page thumbnail/link.
5. Show packet limits when present, for example missing text manifests or text-only generation context.
6. Click an assistant citation chip and show it jumps to the accepted evidence page only.
7. Switch to a conversation with no ready paper scope and ask a general research question to show no-paper conversation mode remains available.

## Boundary Note

This segment shows verified single-turn packet chat and evidence UI. It should not be narrated as a multi-pass autonomous research agent; that belongs to Node 7.

## Node 7 Bounded Orchestrator Segment

1. Start with a scoped hybrid chat question that needs more than one evidence page.
2. Show the visible plan/query trace: conversation-aware query, pass index, and `retrieval_mode="hybrid"`.
3. Capture the first validated evidence packet and its accepted evidence IDs.
4. Highlight an evidence gap from the public trace, such as missing ablation or limitation evidence.
5. Show the second retrieval pass adding new evidence, or stopping with `no_new_evidence` when it repeats the same page.
6. End on the final answer or bounded refusal, with citations restricted to accepted packet pages and the final stop reason visible in the trace.

## Node 7 Boundary Note

This segment demonstrates a server-verified bounded state machine over validated packet retrieval. Do not narrate it as free-form ReAct, full systematic-review automation, dense text retrieval, OCR, cost optimization, or a frontend redesign.

## Node 8 Robustness/Safety Segment

1. Start with no selected/ready paper scope and ask a paper-specific question; show the empty evidence packet and conversation-mode limit.
2. Ask a scoped question whose retrieval returns no accepted evidence; show the `partial` status, no citations, and no paper-grounded claim.
3. Show a repeated-page second pass stopping with `no_new_evidence` in the public trace.
4. Use a synthetic prompt-injection caption and show it is labeled as untrusted evidence while unsafe planner/tool/citation instructions are absent from the public trace.
5. Show an answer where a generated citation outside the accepted packet is stripped.
6. End with a conflicting or low-text evidence packet where the final limits say to verify cited pages or treat the page as visual-first.

## Node 8 Boundary Note

This segment demonstrates deterministic trust and safety regressions for weak, missing, conflicting, low-text, and prompt-injection fixtures. Do not narrate it as comprehensive security proof, OCR robustness, real-corpus robustness, cost modeling, final report acceptance, or final video production.

## Node 9 Commercial Stress Test Segment

1. Open `reports/final/results/cost_benefit.md` on the sensitivity table.
2. Show the 20-PDF evidence-packet base case: API/compute cost, PaperMemory operation time, verification time, and estimated expert-time savings.
3. Briefly switch to the systematic-review pre-screening row to show that conservative assumptions can go negative.
4. Close by saying the business value is first-pass evidence gathering and citation packaging with human verification, not guaranteed ROI or systematic-review replacement.

## Node 9 Boundary Note

This segment is a transparent planning estimate for commercial stress testing. Do not narrate it as production telemetry, validated willingness to pay, feature parity with Elicit or Consensus, product pricing, billing, or final report/video completion.
