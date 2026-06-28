from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import httpx


API = "http://127.0.0.1:8000"
OUT_DIR = Path("artifacts/real-local-test/2026-06-26")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "chat-agentic-results.redacted.json"

REQUIRED = {
    "visrag-core.pdf": "visrag",
    "bm25-exact.pdf": "bm25",
    "agent-robustness.pdf": "robustness",
}


def _safe_error(text: str) -> str:
    text = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[redacted-token]", text)
    text = re.sub(r"(?i)(api[_ -]?key|authorization|bearer)[^,}]{0,120}", r"\1=[redacted]", text)
    text = re.sub(r"[A-Za-z]:\\\\[^\"'<>|]+", "[redacted-local-path]", text)
    return text[:800]


def _papers_by_required_filename() -> dict[str, dict[str, Any]]:
    response = httpx.get(f"{API}/papers", timeout=10)
    response.raise_for_status()
    papers = response.json()["papers"]
    selected: dict[str, dict[str, Any]] = {}
    for filename in REQUIRED:
      matches = [
          paper for paper in papers
          if paper.get("filename") == filename and paper.get("status") == "ready"
      ]
      if not matches:
          raise RuntimeError(f"Missing ready paper for {filename}")
      selected[filename] = sorted(matches, key=lambda paper: paper.get("created_at", ""))[0]
    return selected


def _summary_from_response(result: dict[str, Any], *, image_context_requested: bool) -> dict[str, Any]:
    packet = result.get("evidence_packet") or {}
    trace = result.get("agent_trace") or {}
    actions = trace.get("actions") or []
    stats = result.get("stats") or {}
    text = json.dumps(result, ensure_ascii=False)
    return {
        "http_status": 200,
        "status": result.get("status"),
        "model": result.get("model"),
        "image_context_requested": image_context_requested,
        "requested_max_evidence_images": 10 if image_context_requested else 0,
        "included_image_count": stats.get("included_image_count"),
        "evidence_count": len(result.get("evidence") or []),
        "citation_count": len(packet.get("citations") or []),
        "limits": result.get("limits") or [],
        "packet_limits": packet.get("limits") or [],
        "agent_final_stop_reason": trace.get("final_stop_reason"),
        "agent_states": [action.get("state") for action in actions],
        "agent_action_count": len(actions),
        "paper_scope_count": stats.get("paper_scope_count"),
        "retrieval_attempted": stats.get("retrieval_attempted"),
        "secret_leak_check": {
            "contains_env_key_name": "PAPERMEMORY_BYOK_API_KEY" in text,
            "contains_sk_token_pattern": bool(re.search(r"sk-[A-Za-z0-9_-]{8,}", text)),
            "contains_windows_path": bool(re.search(r"[A-Za-z]:\\\\", text)),
        },
    }


def _post_chat(payload: dict[str, Any]) -> tuple[int, dict[str, Any] | str]:
    response = httpx.post(f"{API}/chat", json=payload, timeout=180)
    try:
        body: dict[str, Any] | str = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body


def main() -> None:
    selected = _papers_by_required_filename()
    paper_ids = [
        selected["visrag-core.pdf"]["paper_id"],
        selected["bm25-exact.pdf"]["paper_id"],
        selected["agent-robustness.pdf"]["paper_id"],
    ]
    base_payload: dict[str, Any] = {
        "question": (
            "Compare page-image search, exact-term BM25 matching, and bounded retry or malicious-evidence "
            "handling. Which pages support each part?"
        ),
        "paper_ids": paper_ids,
        "top_k": 6,
        "retrieval_mode": "hybrid",
        "enable_query_rewrite": True,
        "enable_agentic_retrieval": True,
        "temperature": 0.1,
    }

    attempts: list[dict[str, Any]] = []
    for image_context in (True, False):
        payload = {
            **base_payload,
            "enable_image_context": image_context,
            "max_evidence_images": 10 if image_context else 0,
        }
        status, body = _post_chat(payload)
        if status == 200 and isinstance(body, dict):
            summary = _summary_from_response(body, image_context_requested=image_context)
            attempts.append({"attempt": "image" if image_context else "text", "summary": summary})
            break
        attempts.append(
            {
                "attempt": "image" if image_context else "text",
                "http_status": status,
                "error": _safe_error(json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)),
            }
        )

    final = {
        "selected_papers": {
            filename: {
                "paper_id": paper["paper_id"],
                "title": paper.get("title"),
                "filename": paper.get("filename"),
                "page_count": paper.get("page_count"),
                "status": paper.get("status"),
            }
            for filename, paper in selected.items()
        },
        "attempts": attempts,
    }
    OUT_PATH.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(json.dumps(final, indent=2))

    if not attempts or "summary" not in attempts[-1]:
        raise SystemExit("No successful live BYOK chat attempt.")
    summary = attempts[-1]["summary"]
    assert summary["status"] in {"success", "partial"}
    assert summary["evidence_count"] > 0
    assert summary["citation_count"] > 0
    assert summary["included_image_count"] is not None
    assert summary["included_image_count"] <= 3
    assert summary["agent_final_stop_reason"] in {
        "sufficient",
        "no_new_evidence",
        "budget_exhausted",
        "insufficient_evidence",
    }
    assert "evidence_analysis" in summary["agent_states"]
    assert not any(summary["secret_leak_check"].values())


if __name__ == "__main__":
    main()
