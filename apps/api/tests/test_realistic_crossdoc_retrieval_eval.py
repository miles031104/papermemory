from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.retrieval import run_retrieval_eval as retrieval_eval  # noqa: E402


def test_realistic_crossdoc_fixture_uses_five_user_facing_questions() -> None:
    fixture = retrieval_eval.build_realistic_crossdoc_fixture()

    assert [(row["id"], row["question_type"]) for row in fixture.questions] == [
        ("Q1", "cross_document_synthesis"),
        ("Q2", "numeric_grounding"),
        ("Q3", "taxonomy_reasoning"),
        ("Q4", "defense_reasoning"),
        ("Q5", "claim_scoping"),
    ]
    assert len(fixture.pages) >= 7
    assert all(row["paper_ids"] for row in fixture.questions)
    assert all(row["expected_pages"] for row in fixture.questions)


def test_realistic_crossdoc_methods_show_hybrid_coverage_advantage(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(retrieval_eval, "RESULTS_DIR", tmp_path / "eval-results")
    monkeypatch.setattr(
        retrieval_eval,
        "REALISTIC_CROSSDOC_REPORT_METRICS_PATH",
        tmp_path / "report-results" / "realistic_crossdoc_metrics.md",
        raising=False,
    )

    payload = retrieval_eval.run_realistic_crossdoc_eval(output_prefix="pytest-realistic-crossdoc")
    assert [row["method"] for row in payload["methods"]] == [
        "Keyword overlap baseline",
        "VisRAG page-image retrieval",
        "BM25 text-manifest retrieval",
        "Hybrid page fusion",
    ]
    rows = {row["method"]: row for row in payload["methods"]}

    assert set(rows) == {
        "Keyword overlap baseline",
        "VisRAG page-image retrieval",
        "BM25 text-manifest retrieval",
        "Hybrid page fusion",
    }

    keyword = rows["Keyword overlap baseline"]["metrics"]["evidence_recall_at_5"]
    visrag = rows["VisRAG page-image retrieval"]["metrics"]["evidence_recall_at_5"]
    bm25 = rows["BM25 text-manifest retrieval"]["metrics"]["evidence_recall_at_5"]
    hybrid = rows["Hybrid page fusion"]["metrics"]["evidence_recall_at_5"]

    assert keyword < visrag
    assert keyword < bm25
    assert hybrid > visrag
    assert hybrid > bm25

    hybrid_full_support = rows["Hybrid page fusion"]["metrics"]["full_support_at_5"]
    assert hybrid_full_support >= rows["VisRAG page-image retrieval"]["metrics"]["full_support_at_5"]
    assert hybrid_full_support >= rows["BM25 text-manifest retrieval"]["metrics"]["full_support_at_5"]


def test_realistic_crossdoc_outputs_are_written(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(retrieval_eval, "RESULTS_DIR", tmp_path / "eval-results")
    monkeypatch.setattr(
        retrieval_eval,
        "REALISTIC_CROSSDOC_REPORT_METRICS_PATH",
        tmp_path / "report-results" / "realistic_crossdoc_metrics.md",
        raising=False,
    )

    payload = retrieval_eval.run_realistic_crossdoc_eval(output_prefix="realistic-crossdoc")

    json_path = tmp_path / "eval-results" / "realistic-crossdoc.json"
    csv_path = tmp_path / "eval-results" / "realistic-crossdoc.csv"
    md_path = tmp_path / "eval-results" / "realistic-crossdoc.md"
    report_path = tmp_path / "report-results" / "realistic_crossdoc_metrics.md"

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()
    assert report_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["mode"] == "realistic-crossdoc"
    assert loaded["methods"][0]["method"] == payload["methods"][0]["method"]
    assert "VisRAG page-image retrieval" in report_path.read_text(encoding="utf-8")
    assert "Hybrid page fusion" in report_path.read_text(encoding="utf-8")
