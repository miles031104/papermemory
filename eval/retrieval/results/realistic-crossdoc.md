# Realistic Cross-Document Retrieval Metrics

Mode: realistic cross-document retrieval fixture from `eval/skill_security_crossdoc_testset.json`.

## Summary

| Method | Mean evidence recall@5 | Fully supported questions | Mean required pages |
| --- | ---: | ---: | ---: |
| Keyword overlap baseline | 0.80 | 1/5 | 4.20 |
| VisRAG page-image retrieval | 0.81 | 2/5 | 4.20 |
| BM25 text-manifest retrieval | 0.82 | 2/5 | 4.20 |
| Hybrid page fusion | 0.85 | 3/5 | 4.20 |

## Per-Question Results

### Keyword overlap baseline

| ID | Type | Expected pages | Evidence pages@5 | Evidence recall@5 | Full support@5 |
| --- | --- | --- | --- | ---: | --- |
| Q1 | cross_document_synthesis | skill_inject:1, skill_inject:3, wild_skills:1, trojan_whisper:1 | wild_skills:1, skill_inject:1, trojan_whisper:1, skill_inject:4, trojan_whisper:2 | 75.0% | no |
| Q2 | numeric_grounding | skill_inject:1, wild_skills:1, wild_skills:2, trojan_whisper:1 | skill_inject:1, wild_skills:1, trojan_whisper:1, skill_inject:4, trojan_whisper:2 | 75.0% | no |
| Q3 | taxonomy_reasoning | wild_skills:1, wild_skills:2, trojan_whisper:1, skill_inject:3 | skill_inject:1, skill_inject:3, trojan_whisper:1, trojan_whisper:2, wild_skills:1 | 75.0% | no |
| Q4 | defense_reasoning | skill_inject:1, skill_inject:4, wild_skills:2, trojan_whisper:1 | wild_skills:1, skill_inject:4, skill_inject:1, trojan_whisper:1, trojan_whisper:2 | 75.0% | no |
| Q5 | claim_scoping | skill_inject:1, skill_inject:4, wild_skills:1, trojan_whisper:1, trojan_whisper:2 | wild_skills:1, skill_inject:1, skill_inject:4, trojan_whisper:1, trojan_whisper:2 | 100.0% | yes |

### VisRAG page-image retrieval

| ID | Type | Expected pages | Evidence pages@5 | Evidence recall@5 | Full support@5 |
| --- | --- | --- | --- | ---: | --- |
| Q1 | cross_document_synthesis | skill_inject:1, skill_inject:3, wild_skills:1, trojan_whisper:1 | skill_inject:3, skill_inject:1, wild_skills:1, trojan_whisper:1, skill_inject:4 | 100.0% | yes |
| Q2 | numeric_grounding | skill_inject:1, wild_skills:1, wild_skills:2, trojan_whisper:1 | wild_skills:2, wild_skills:1, trojan_whisper:1, skill_inject:1, trojan_whisper:2 | 100.0% | yes |
| Q3 | taxonomy_reasoning | wild_skills:1, wild_skills:2, trojan_whisper:1, skill_inject:3 | skill_inject:3, skill_inject:1, skill_inject:4, trojan_whisper:1, trojan_whisper:2 | 50.0% | no |
| Q4 | defense_reasoning | skill_inject:1, skill_inject:4, wild_skills:2, trojan_whisper:1 | skill_inject:4, trojan_whisper:2, skill_inject:1, skill_inject:3, trojan_whisper:1 | 75.0% | no |
| Q5 | claim_scoping | skill_inject:1, skill_inject:4, wild_skills:1, trojan_whisper:1, trojan_whisper:2 | skill_inject:1, trojan_whisper:1, trojan_whisper:2, skill_inject:4, skill_inject:3 | 80.0% | no |

### BM25 text-manifest retrieval

| ID | Type | Expected pages | Evidence pages@5 | Evidence recall@5 | Full support@5 |
| --- | --- | --- | --- | ---: | --- |
| Q1 | cross_document_synthesis | skill_inject:1, skill_inject:3, wild_skills:1, trojan_whisper:1 | trojan_whisper:1, wild_skills:1, skill_inject:1, wild_skills:2, skill_inject:3 | 100.0% | yes |
| Q2 | numeric_grounding | skill_inject:1, wild_skills:1, wild_skills:2, trojan_whisper:1 | skill_inject:1, wild_skills:1, trojan_whisper:1, skill_inject:3, trojan_whisper:2 | 75.0% | no |
| Q3 | taxonomy_reasoning | wild_skills:1, wild_skills:2, trojan_whisper:1, skill_inject:3 | skill_inject:3, trojan_whisper:2, trojan_whisper:1, skill_inject:1, wild_skills:2 | 75.0% | no |
| Q4 | defense_reasoning | skill_inject:1, skill_inject:4, wild_skills:2, trojan_whisper:1 | skill_inject:1, skill_inject:4, wild_skills:1, trojan_whisper:1, wild_skills:2 | 100.0% | yes |
| Q5 | claim_scoping | skill_inject:1, skill_inject:4, wild_skills:1, trojan_whisper:1, trojan_whisper:2 | wild_skills:1, trojan_whisper:2, skill_inject:4 | 60.0% | no |

### Hybrid page fusion

| ID | Type | Expected pages | Evidence pages@5 | Evidence recall@5 | Full support@5 |
| --- | --- | --- | --- | ---: | --- |
| Q1 | cross_document_synthesis | skill_inject:1, skill_inject:3, wild_skills:1, trojan_whisper:1 | trojan_whisper:1, skill_inject:1, wild_skills:1, skill_inject:3, wild_skills:2 | 100.0% | yes |
| Q2 | numeric_grounding | skill_inject:1, wild_skills:1, wild_skills:2, trojan_whisper:1 | wild_skills:1, skill_inject:1, trojan_whisper:1, trojan_whisper:2, wild_skills:2 | 100.0% | yes |
| Q3 | taxonomy_reasoning | wild_skills:1, wild_skills:2, trojan_whisper:1, skill_inject:3 | skill_inject:3, skill_inject:1, trojan_whisper:2, trojan_whisper:1, skill_inject:4 | 50.0% | no |
| Q4 | defense_reasoning | skill_inject:1, skill_inject:4, wild_skills:2, trojan_whisper:1 | skill_inject:4, skill_inject:1, trojan_whisper:1, trojan_whisper:2, wild_skills:1 | 75.0% | no |
| Q5 | claim_scoping | skill_inject:1, skill_inject:4, wild_skills:1, trojan_whisper:1, trojan_whisper:2 | trojan_whisper:2, skill_inject:4, skill_inject:1, wild_skills:1, trojan_whisper:1 | 100.0% | yes |

## Boundary

- Controlled five-question cross-document retrieval fixture derived from the skill-security demo corpus; not a broad scholarly-corpus benchmark.
- This is a retrieval-only artifact; it does not measure generated answer quality, citation prose, or abstention behavior.
- Live answer-quality behavior remains a separate artifact and should not be inferred from these retrieval metrics.
