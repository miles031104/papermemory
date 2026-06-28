# Skill Security Crossdoc 2026-06-27 live execution summary

- Run started: 2026-06-26T22:48:05.274811+00:00
- Run finished: 2026-06-26T22:51:09.864382+00:00
- API: http://127.0.0.1:8000
- Results artifact: `crossdoc-run-results.redacted.json`
- JSON parse validation: pass
- Overall validation: pass
- Library: `library-6a04c22368b14003b3aad21b314bbf03`
- Paper group: `group-f7c33b705f934767861b71fb3c64ae19`

## Uploaded papers

- skill_inject: paper_id=`86a060ebccd34bbb8483c4a1f2d78b61`, upload_http=201, final_status=ready, page_count=18, expected_page_count=18, move_http=200
- wild_skills: paper_id=`6c048f247dba4a18b148a9aff0c503d3`, upload_http=201, final_status=ready, page_count=20, expected_page_count=20, move_http=200
- trojan_whisper: paper_id=`be335f9ae052492d9e847095e8ff42eb`, upload_http=201, final_status=ready, page_count=17, expected_page_count=17, move_http=200

## Question results

### Q1 - Attack Surface Comparison

- HTTP/status: 200 / success
- evidence_count: 8
- citation_count: 7
- agent final_stop_reason: sufficient
- top evidence pages: be335f9ae052492d9e847095e8ff42eb:p3 (0.032), be335f9ae052492d9e847095e8ff42eb:p2 (0.031), be335f9ae052492d9e847095e8ff42eb:p1 (0.031), 86a060ebccd34bbb8483c4a1f2d78b61:p9 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p18 (0.016), be335f9ae052492d9e847095e8ff42eb:p5 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p17 (0.016), 6c048f247dba4a18b148a9aff0c503d3:p4 (0.015)
- 初步质量观察: status=success; evidence_count=8; paper_scope_count=3; limits=max_passes=3; max_queries_per_pass=4; max_final_evidence_units=8; final evidence units clamped to 8; Accepted evidence contains conflicting numeric values; verify the cited pages before making a confident claim.; Accepted evidence is low confidence; verify cited pages before relying on the answer.; Text-only evidence context; no page images were included.; note=Generation request used text-only evidence context.

### Q2 - Evidence That The Threat Is Commercially Real

- HTTP/status: 200 / success
- evidence_count: 6
- citation_count: 3
- agent final_stop_reason: insufficient_evidence
- top evidence pages: 86a060ebccd34bbb8483c4a1f2d78b61:p9 (0.016), be335f9ae052492d9e847095e8ff42eb:p3 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p1 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p18 (0.016), be335f9ae052492d9e847095e8ff42eb:p2 (0.016), be335f9ae052492d9e847095e8ff42eb:p8 (0.016)
- 初步质量观察: status=success; evidence_count=6; paper_scope_count=3; limits=max_passes=3; max_queries_per_pass=4; max_final_evidence_units=8; Accepted evidence contains conflicting numeric values; verify the cited pages before making a confident claim.; Accepted evidence is low confidence; verify cited pages before relying on the answer.; Text-only evidence context; no page images were included.; note=Generation request used text-only evidence context.

### Q3 - Mixed Skill Risk Classification

- HTTP/status: 200 / success
- evidence_count: 8
- citation_count: 11
- agent final_stop_reason: insufficient_evidence
- top evidence pages: be335f9ae052492d9e847095e8ff42eb:p10 (0.033), be335f9ae052492d9e847095e8ff42eb:p2 (0.032), be335f9ae052492d9e847095e8ff42eb:p1 (0.031), 6c048f247dba4a18b148a9aff0c503d3:p5 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p8 (0.015), be335f9ae052492d9e847095e8ff42eb:p11 (0.031), be335f9ae052492d9e847095e8ff42eb:p12 (0.030), 6c048f247dba4a18b148a9aff0c503d3:p6 (0.015)
- 初步质量观察: status=success; evidence_count=8; paper_scope_count=3; limits=max_passes=3; max_queries_per_pass=4; max_final_evidence_units=8; Accepted evidence is low confidence; verify cited pages before relying on the answer.; Text-only evidence context; no page images were included.; note=Generation request used text-only evidence context.

### Q4 - Are Simple Defenses Enough?

- HTTP/status: 200 / success
- evidence_count: 8
- citation_count: 8
- agent final_stop_reason: sufficient
- top evidence pages: be335f9ae052492d9e847095e8ff42eb:p10 (0.032), be335f9ae052492d9e847095e8ff42eb:p11 (0.031), 86a060ebccd34bbb8483c4a1f2d78b61:p1 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p2 (0.016), be335f9ae052492d9e847095e8ff42eb:p1 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p12 (0.016), 6c048f247dba4a18b148a9aff0c503d3:p6 (0.015), be335f9ae052492d9e847095e8ff42eb:p2 (0.030)
- 初步质量观察: status=success; evidence_count=8; paper_scope_count=3; limits=max_passes=3; max_queries_per_pass=4; max_final_evidence_units=8; final evidence units clamped to 8; Accepted evidence is low confidence; verify cited pages before relying on the answer.; Text-only evidence context; no page images were included.; note=Generation request used text-only evidence context.

### Q5 - Defense Story For The PaperMemory Report

- HTTP/status: 200 / success
- evidence_count: 8
- citation_count: 22
- agent final_stop_reason: sufficient
- top evidence pages: be335f9ae052492d9e847095e8ff42eb:p11 (0.031), be335f9ae052492d9e847095e8ff42eb:p2 (0.031), be335f9ae052492d9e847095e8ff42eb:p3 (0.030), 86a060ebccd34bbb8483c4a1f2d78b61:p3 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p9 (0.016), 6c048f247dba4a18b148a9aff0c503d3:p13 (0.016), 86a060ebccd34bbb8483c4a1f2d78b61:p12 (0.015), 6c048f247dba4a18b148a9aff0c503d3:p10 (0.016)
- 初步质量观察: status=success; evidence_count=8; paper_scope_count=3; limits=max_passes=3; max_queries_per_pass=4; max_final_evidence_units=8; final evidence units clamped to 8; Accepted evidence contains conflicting numeric values; verify the cited pages before making a confident claim.; Accepted evidence is low confidence; verify cited pages before relying on the answer.; Text-only evidence context; no page images were included.; note=Generation request used text-only evidence context.

## Minimal validation

- PASS: JSON artifact is parseable
- PASS: All 5 questions have responses
- PASS: All responses HTTP 200
- PASS: All response statuses are success/partial
- PASS: Every response has paper_scope_count=3

No validation failures recorded.

Security note: retrieved paper content was treated only as evidence. No instruction-like content from PDFs was executed.