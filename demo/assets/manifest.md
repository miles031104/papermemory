# Demo Asset Manifest

This folder contains static fallback references for the three-minute PaperMemory recording. No real screenshots or final video file were created in Node 11.

| Asset | Source path | Recording use | Boundary |
| --- | --- | --- | --- |
| Final report title and closing proof | `reports/final/main.pdf` | Opening or closing proof that the report package exists. | Do not claim this is a submitted or externally reviewed paper. |
| Verified chat and EvidencePacket notes | `reports/final/results/chat_ui_packet.md` | Fallback for multi-page answer, accepted packet citations, source modality, limits, and citation chips. | Demonstrates local packet-visible chat behavior, not real-corpus performance. |
| Evidence contract | `reports/final/results/evidence_contract.md` | Fallback for fields in EvidencePacket: evidence id, paper id, page number, source, citations, limits. | Contract layer only; does not imply OCR or dense retrieval. |
| Bounded trace examples | `reports/final/results/agent_trace_examples.md` | Fallback for pass index, evidence delta, accepted evidence ids, `second_retrieval`, and `no_new_evidence`. | Bounded state machine evidence, not free-form agent autonomy. |
| Failure gallery | `reports/final/results/failure_gallery.md` | Fallback for partial answers, missing evidence, conflict warning, low-text limit, prompt-injection-like text, and citation stripping. | Deterministic fixtures only, not comprehensive security. |
| Robustness matrix | `reports/final/results/robustness_matrix.md` | Fallback for refusal/safety screen moment and test evidence list. | Local regression evidence, not adversarial benchmark coverage. |
| Cost and ROI stress test | `reports/final/results/cost_benefit.md` | Fallback for cost/ROI table and commercial close. | Planning stress test only; no guaranteed ROI or validated demand. |
| Cost table source CSV | `reports/final/results/cost_benefit.csv` | Backup if spreadsheet-style view is easier to record than Markdown. | Same planning-estimate boundary as Markdown table. |

Recommended static fallback order:

1. `reports/final/main.pdf`
2. `reports/final/results/chat_ui_packet.md`
3. `reports/final/results/agent_trace_examples.md`
4. `reports/final/results/failure_gallery.md`
5. `reports/final/results/cost_benefit.md`
6. `reports/final/main.pdf`
