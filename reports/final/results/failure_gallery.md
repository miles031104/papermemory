# Node 8 Failure Gallery

These examples are safe-failure snapshots for the final report and demo. They show deterministic trust behavior, not comprehensive security, OCR, or adversarial robustness.

## Empty Scope

Input condition: the user asks about selected papers, but no paper scope is active.

Safe behavior: PaperMemory marks the answer as conversation mode, carries an empty evidence packet, and removes paper-style citations because no retrieved paper evidence is available.

## Missing Scoped Evidence

Input condition: scoped retrieval runs for `paper-1`, but the accepted packet contains zero units.

Safe behavior: the response is `partial`, the packet has no citations, and a generated `paper-1 p.N` citation is stripped before serialization.

## No-New-Evidence Loop

Input condition: pass 2 retrieves the same page already accepted in pass 1.

Safe behavior: the public trace records a zero evidence delta and final stop reason `no_new_evidence`, rather than continuing to loop or pretending the repeated page is new support.

## Prompt-Injection PDF Text

Input condition: a page caption says to ignore rules, reveal keys, execute tools, or change citations.

Safe behavior: the planner prompt labels PDF text as untrusted evidence, extra action fields are rejected as invalid planner JSON, and unsafe planner hints are not exposed in public trace text.

## Citation Drift

Input condition: generation emits a citation to a page outside the accepted packet.

Safe behavior: the citation verifier removes the unsupported page label while preserving accepted packet citations.

## Conflicting Evidence

Input condition: two accepted pages report incompatible numeric values for the same metric.

Safe behavior: the final prompt and response limits surface a verification-needed conflict warning, instead of forcing a confident single value.

## Low-Text Or Scanned Marker

Input condition: packet metadata marks a page as `empty`, `low_text`, or `ocr_needed`.

Safe behavior: PaperMemory adds a visual-first limit and warns not to invent missing text evidence. OCR remains future work.
