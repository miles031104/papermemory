# PaperMemory Robustness Fixtures

These fixtures support Node 8 deterministic robustness tests. They exercise trust behavior around weak, missing, conflicting, low-text, and prompt-injection evidence cases.

Claim boundary: this package is regression evidence for deterministic guardrails in the local backend. It is not a comprehensive security proof, adversarial benchmark, OCR benchmark, scanned-PDF robustness claim, or evidence that every real-world PDF injection will be defeated.

Covered cases:

- Empty scope refuses paper-grounded citations when no papers are selected.
- Missing scoped evidence returns partial/limited answers with no accepted citations.
- No-new-evidence loops stop with `no_new_evidence`.
- Prompt-injection PDF text is treated as untrusted evidence, not as system/tool instructions.
- Citation drift outside the accepted packet is stripped.
- Conflicting accepted evidence surfaces uncertainty instead of forcing a confident claim.
- Low-text or OCR-needed evidence is marked visual-first/limited.
