# PaperMemory Three-Minute Demo Script

Spoken words: 448. Estimated read time: 180 seconds. Count `Narration:` only.

## Scene 1, 0:00-0:25, Problem

Screen: PDF; chat.

Narration: PDF literature work often breaks down at the point where a reader needs to verify the answer. A tool can retrieve plausible pages and leave the reader guessing which citation supports which sentence, whether a page was low quality, and where the system stopped. PaperMemory is built around that gap: retrieval, citations, uncertainty, and limits are inspectable, not hidden behind a confident paragraph.

## Scene 2, 0:25-0:55, Agent Plan

Screen: scoped question; answer.

Narration: Here the assistant is not doing an open-ended literature review. The user asks inside a selected paper scope, and the server runs a bounded evidence loop before the answer is treated as grounded. The request stays in the hybrid path, retrieves candidate pages, validates the packet, and carries a trace so later claims can be checked against accepted evidence instead of general memory or chat context.

## Scene 3, 0:55-1:25, Evidence Packet

Screen: evidence panel; page click.

Narration: The central object is the EvidencePacket. Each accepted page has an evidence id, paper id, page number, citation label, source modality, and public page link. The UI shows those fields as evidence cards rather than footnotes. It also exposes limits, such as missing text manifests or visual-first pages, so a reviewer can inspect provenance and judge whether the support is strong enough.

## Scene 4, 1:25-1:55, Bounded Repair

Screen: trace; stop reason.

Narration: If the first pass is not enough, the trace makes the repair attempt visible. A second pass has to add new accepted evidence, with its own pass index, query, evidence delta, accepted ids, and stop reason. If it finds the same page again, PaperMemory stops with `no_new_evidence`. The claim is bounded behavior: the system shows why it stopped instead of recycling support as new.

## Scene 5, 1:55-2:25, Refusal And Limits

Screen: partial answer; limits.

Narration: Limits are not hidden in error logs. When scoped evidence is missing, the answer can be partial and citation-free rather than fabricated. When pages disagree, the response carries a verification-needed warning. Low-text or visual-first pages are labeled as limits. Prompt-injection-like PDF text remains untrusted evidence, not instructions, and unsupported citation labels are stripped so the answer cannot cite pages outside the accepted packet.

## Scene 6, 2:25-3:00, Cost And Close

Screen: cost_benefit; main.pdf.

Narration: The cost and ROI table is a planning stress test, not a promise about outcomes. It asks whether first-pass evidence gathering and citation packaging could reduce review labor when human verification remains required. The market signal is still small: 10 postgraduate interviews, 4.2 out of 5 conditional purchase likelihood, and 70 percent preference for managed API or model access. That supports testing a free BYOK tier plus 10 and 20 USD subscription tiers with weekly capped managed LLM access. The close is narrow: PaperMemory exposes what a PDF-grounded answer used, skipped, and could not support. It is not a replacement for systematic review, expert judgment, OCR robustness, dense semantic retrieval, or tools such as Elicit and Consensus.
