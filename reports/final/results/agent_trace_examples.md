# Node 7 Agent Trace Examples

Node 7 adds a bounded backend state machine over validated packet retrieval. It is not free-form ReAct, not LangGraph/CrewAI, and not full systematic-review automation. Planner JSON is only an untrusted hint; the server validates decisions, executes retrieval, clamps budgets, dedupes evidence, and returns public-safe trace actions.

## Sufficient Trace

```json
{
  "trace_id": "trace-example-sufficient",
  "max_passes": 3,
  "max_queries_per_pass": 4,
  "final_stop_reason": "sufficient",
  "actions": [
    {
      "state": "query_rewrite",
      "pass_index": 0,
      "query": "paper method and evaluation evidence",
      "note": "conversation-aware query prepared"
    },
    {
      "state": "first_retrieval",
      "pass_index": 1,
      "query": "paper method and evaluation evidence",
      "retrieval_mode": "hybrid",
      "evidence_ids": ["ev-paper-a-p3", "ev-paper-a-p7"],
      "new_evidence_ids": ["ev-paper-a-p3", "ev-paper-a-p7"],
      "evidence_delta_count": 2
    },
    {
      "state": "evidence_analysis",
      "pass_index": 1,
      "retrieval_mode": "hybrid",
      "evidence_ids": ["ev-paper-a-p3", "ev-paper-a-p7"],
      "missing_evidence": [],
      "stop_reason": "sufficient",
      "note": "planner confidence: high"
    },
    {
      "state": "answer",
      "pass_index": 1,
      "evidence_ids": ["ev-paper-a-p3", "ev-paper-a-p7"],
      "stop_reason": "sufficient"
    }
  ],
  "limits": ["max_passes=3", "max_queries_per_pass=4", "max_final_evidence_units=8"]
}
```

## No-New-Evidence Trace

```json
{
  "trace_id": "trace-example-no-new-evidence",
  "max_passes": 3,
  "max_queries_per_pass": 4,
  "final_stop_reason": "no_new_evidence",
  "actions": [
    {
      "state": "first_retrieval",
      "pass_index": 1,
      "query": "paper limitation evidence",
      "retrieval_mode": "hybrid",
      "evidence_ids": ["ev-paper-b-p9"],
      "new_evidence_ids": ["ev-paper-b-p9"],
      "evidence_delta_count": 1
    },
    {
      "state": "evidence_analysis",
      "pass_index": 1,
      "retrieval_mode": "hybrid",
      "evidence_ids": ["ev-paper-b-p9"],
      "missing_evidence": ["independent ablation page"],
      "stop_reason": null,
      "note": "planner confidence: medium"
    },
    {
      "state": "second_retrieval",
      "pass_index": 2,
      "query": "paper limitation ablation evidence",
      "retrieval_mode": "hybrid",
      "evidence_ids": ["ev-paper-b-p9"],
      "new_evidence_ids": [],
      "evidence_delta_count": 0
    },
    {
      "state": "sufficiency_check",
      "pass_index": 2,
      "evidence_ids": ["ev-paper-b-p9"],
      "evidence_delta_count": 0,
      "stop_reason": "no_new_evidence",
      "note": "second pass evidence delta checked"
    },
    {
      "state": "answer",
      "pass_index": 2,
      "evidence_ids": ["ev-paper-b-p9"],
      "stop_reason": "no_new_evidence"
    }
  ],
  "limits": ["max_passes=3", "max_queries_per_pass=4", "max_final_evidence_units=8"]
}
```

## Report Boundary

The measurable Node 7 contribution is bounded evidence seeking: accepted evidence IDs, per-pass evidence deltas, stop reasons, and validated final packets. It does not claim exhaustive coverage of a paper collection, autonomous literature-review completeness, OCR robustness, dense text semantic retrieval, or cost optimization.
