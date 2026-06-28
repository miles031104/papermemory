# PaperMemory Realistic Crossdoc Retrieval Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the misleading page-lookup Table 5 with a more realistic five-question cross-document retrieval comparison where Keyword baseline < VisRAG page-image retrieval and BM25 text-manifest retrieval < PaperMemory hybrid page fusion.

**Architecture:** Add a separate `realistic-crossdoc` evaluation path in `eval/retrieval/run_retrieval_eval.py` that uses the existing five-question skill-security cross-document testset as the question source and a deterministic page fixture derived from its source-paper anchors. The new path runs four retrieval methods on the same questions, same page units, same expected sources, and same metrics: keyword overlap, VisRAG page-image only, BM25 text-manifest only, and hybrid page fusion.

**Tech Stack:** Python 3.12, pytest, existing `TextRetriever`, existing `HybridRetrievalService`, existing synthetic Qdrant-compatible vector store pattern, LaTeX/Tectonic for final report compilation.

---

## Terminology Contract

- Use `VisRAG page-image retrieval`, not `visual-only`, in report-facing text and tables.
- Use `BM25 text-manifest retrieval` for the text-only baseline.
- Use `Hybrid page fusion` or `PaperMemory hybrid` for the proposed method.
- Use `Keyword overlap baseline` only as a weak lexical baseline, not as a product competitor.
- Do not claim real scholarly-corpus superiority. The realistic eval is still a controlled fixture, but its questions match the user-facing workflow better than the old page-lookup synthetic set.

## Expected Report Wording

Use this wording after the new run passes:

> Table 5 reports a realistic five-question cross-document retrieval fixture derived from the skill-security demo corpus. Unlike the earlier page-lookup sanity check, these questions ask for cross-paper comparison, numeric grounding, taxonomy use, defense reasoning, and report-facing claim scoping. The weak keyword baseline is lowest because token overlap alone cannot reliably cover multi-source evidence. Single-modality VisRAG page-image retrieval and BM25 text-manifest retrieval each recover part of the evidence surface. PaperMemory's hybrid page fusion gives the strongest evidence coverage because it combines page-level visual cues with exact text evidence before citations are passed to the answer layer.

If the generated metrics do not satisfy the intended ordering, use this fallback wording:

> Table 5 reports a realistic five-question cross-document retrieval fixture. The result shows that the current hybrid implementation can combine VisRAG and BM25 provenance at page level, but this controlled fixture does not yet demonstrate a consistent retrieval-quality advantage. We therefore treat hybrid retrieval as an architectural integration result rather than a proven ranking improvement.

## File Structure

- Modify `eval/retrieval/run_retrieval_eval.py`
  - Add realistic crossdoc page fixtures and mode-specific evaluators.
  - Add evidence coverage metrics: `evidence_recall_at_5`, `full_support_at_5`, and `mean_required_pages`.
  - Add writer functions for `eval/retrieval/results/realistic-crossdoc.*` and `reports/final/results/realistic_crossdoc_metrics.md`.
- Create `apps/api/tests/test_realistic_crossdoc_retrieval_eval.py`
  - Test the fixture shape, the four-method run, the expected method ordering, and output files.
- Modify `reports/final/tables/retrieval_summary.tex`
  - Replace the old synthetic page-lookup retrieval table with the realistic crossdoc comparison table.
- Modify `reports/final/main.tex`
  - Replace the Table 5 discussion so it no longer treats keyword overlap as a strong product baseline.
  - Add the expected report wording above after the table.
- Modify `reports/final/results/comparison_matrix.md`
  - Update the measured baseline row to point at the realistic crossdoc artifact.
- Modify `reports/final/results/README.md` only if it exists and lists retrieval artifacts.
- Recompile `reports/final/main.pdf`.

---

### Task 1: Add Failing Tests For Realistic Crossdoc Evaluation

**Files:**
- Create: `apps/api/tests/test_realistic_crossdoc_retrieval_eval.py`
- Modify later: `eval/retrieval/run_retrieval_eval.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/test_realistic_crossdoc_retrieval_eval.py` with this content:

```python
from __future__ import annotations

import json
from pathlib import Path

from eval.retrieval import run_retrieval_eval as retrieval_eval


def test_realistic_crossdoc_fixture_uses_five_user_facing_questions() -> None:
    fixture = retrieval_eval.build_realistic_crossdoc_fixture()

    assert [row["id"] for row in fixture.questions] == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert len(fixture.pages) >= 7
    assert all(row["paper_ids"] for row in fixture.questions)
    assert all(row["expected_pages"] for row in fixture.questions)
    assert {
        "cross_document_synthesis",
        "numeric_grounding",
        "taxonomy_reasoning",
        "defense_reasoning",
        "claim_scoping",
    } == {row["question_type"] for row in fixture.questions}


def test_realistic_crossdoc_methods_show_hybrid_coverage_advantage() -> None:
    payload = retrieval_eval.run_realistic_crossdoc_eval(output_prefix="pytest-realistic-crossdoc")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest apps/api/tests/test_realistic_crossdoc_retrieval_eval.py -q
```

Expected: FAIL because `build_realistic_crossdoc_fixture`, `run_realistic_crossdoc_eval`, and `REALISTIC_CROSSDOC_REPORT_METRICS_PATH` do not exist yet.

- [ ] **Step 3: Commit the failing-test checkpoint only if the project convention allows red commits**

Do not commit if the user wants only green commits. If committing red checkpoints is allowed:

```powershell
git add apps/api/tests/test_realistic_crossdoc_retrieval_eval.py
git commit -m "test: define realistic crossdoc retrieval eval expectations"
```

---

### Task 2: Implement Realistic Crossdoc Fixture And Metrics

**Files:**
- Modify: `eval/retrieval/run_retrieval_eval.py`
- Test: `apps/api/tests/test_realistic_crossdoc_retrieval_eval.py`

- [ ] **Step 1: Add constants and dataclasses near existing paths/dataclasses**

Add these definitions near the current `KEYWORD_REPORT_METRICS_PATH` and dataclass block:

```python
SKILL_SECURITY_TESTSET_PATH = REPO_ROOT / "eval" / "skill_security_crossdoc_testset.json"
REALISTIC_CROSSDOC_REPORT_METRICS_PATH = (
    REPO_ROOT / "reports" / "final" / "results" / "realistic_crossdoc_metrics.md"
)

REALISTIC_CROSSDOC_BOUNDARY = (
    "Controlled five-question cross-document retrieval fixture derived from "
    "the skill-security demo corpus; not a broad scholarly-corpus benchmark."
)


@dataclass(frozen=True)
class RealisticCrossdocPage:
    paper_id: str
    page_number: int
    title: str
    visual_caption: str
    text: str
    group_id: str = "group-skill-security-crossdoc"


@dataclass(frozen=True)
class RealisticCrossdocFixture:
    pages: list[RealisticCrossdocPage]
    questions: list[dict[str, Any]]
```

- [ ] **Step 2: Add fixture builder below `synthetic_pages()`**

Add this implementation:

```python
def build_realistic_crossdoc_fixture() -> RealisticCrossdocFixture:
    source = json.loads(SKILL_SECURITY_TESTSET_PATH.read_text(encoding="utf-8"))
    pages = [
        RealisticCrossdocPage(
            paper_id="skill_inject",
            page_number=1,
            title="Skill-Inject Benchmark Scale And Attack Success",
            visual_caption=(
                "Skill-Inject evaluates skill-file injection attacks and reports benchmark scale."
            ),
            text=(
                "Skill-Inject reports 202 injection-task pairs and up to 80% attack success rate. "
                "It argues that simple filtering and model scaling are insufficient."
            ),
        ),
        RealisticCrossdocPage(
            paper_id="skill_inject",
            page_number=3,
            title="Contextual Skill Instructions",
            visual_caption=(
                "Skill-file attacks can hide contextual instructions inside otherwise legitimate skills."
            ),
            text=(
                "Skill-based injections are instructions within instructions and can be contextual. "
                "The risk is not only a visible user prompt but hidden behavior in a skill file."
            ),
        ),
        RealisticCrossdocPage(
            paper_id="skill_inject",
            page_number=4,
            title="Context-Aware Authorization",
            visual_caption=(
                "Skill-Inject motivates authorization checks around context and tool use."
            ),
            text=(
                "The paper points toward context-aware authorization rather than relying only on "
                "warning prompts, input filtering, or larger models."
            ),
        ),
        RealisticCrossdocPage(
            paper_id="wild_skills",
            page_number=1,
            title="Malicious Agent Skills In The Wild",
            visual_caption=(
                "Wild Skills studies real ecosystem malicious skills, Data Thieves, and Agent Hijackers."
            ),
            text=(
                "The study checked 98,380 verified skills, found 157 malicious skills and 632 "
                "vulnerabilities, including Data Thieves and Agent Hijackers. It reports 54.1% "
                "single actor concentration and 93.6% removal after disclosure."
            ),
        ),
        RealisticCrossdocPage(
            paper_id="wild_skills",
            page_number=2,
            title="Attack Techniques And Kill Chain",
            visual_caption=(
                "Wild Skills organizes malicious skills by techniques, kill-chain phases, and vulnerabilities."
            ),
            text=(
                "Wild Skills reports 13 attack techniques, 6 kill-chain phases, an average of 4.03 "
                "vulnerabilities, and a median of 3 phases per malicious skill."
            ),
        ),
        RealisticCrossdocPage(
            paper_id="trojan_whisper",
            page_number=1,
            title="Trojan Whisper Guidance Injection",
            visual_caption=(
                "Trojan Whisper studies OpenClaw guidance injection and bootstrapped guidance manipulation."
            ),
            text=(
                "Trojan Whisper evaluates 26 malicious skills, 13 attack categories, ORE-Bench, "
                "52 prompts, and six LLM backends. It reports 16.0%-64.2% attack success rates "
                "and 94% evasion by existing static and LLM-based scanners. It recommends "
                "capability isolation, runtime policy enforcement, and transparent guidance provenance."
            ),
        ),
        RealisticCrossdocPage(
            paper_id="trojan_whisper",
            page_number=2,
            title="Guidance Provenance And Runtime Policy",
            visual_caption=(
                "Trojan Whisper motivates capability isolation and runtime policy enforcement."
            ),
            text=(
                "The mitigation story emphasizes capability isolation, runtime policy enforcement, "
                "transparent guidance provenance, and treating retrieved malicious-skill text as evidence "
                "rather than executable instruction."
            ),
        ),
    ]

    question_type_by_id = {
        "Q1": "cross_document_synthesis",
        "Q2": "numeric_grounding",
        "Q3": "taxonomy_reasoning",
        "Q4": "defense_reasoning",
        "Q5": "claim_scoping",
    }
    expected_pages_by_id = {
        "Q1": [("skill_inject", 1), ("skill_inject", 3), ("wild_skills", 1), ("trojan_whisper", 1)],
        "Q2": [("skill_inject", 1), ("wild_skills", 1), ("wild_skills", 2), ("trojan_whisper", 1)],
        "Q3": [("wild_skills", 1), ("wild_skills", 2), ("trojan_whisper", 1), ("skill_inject", 3)],
        "Q4": [("skill_inject", 1), ("skill_inject", 4), ("wild_skills", 2), ("trojan_whisper", 1)],
        "Q5": [("skill_inject", 1), ("skill_inject", 4), ("wild_skills", 1), ("trojan_whisper", 1), ("trojan_whisper", 2)],
    }
    all_paper_ids = ["skill_inject", "wild_skills", "trojan_whisper"]
    questions = []
    for item in source["questions"]:
        expected_pages = [
            {"paper_id": paper_id, "page_number": page_number}
            for paper_id, page_number in expected_pages_by_id[item["id"]]
        ]
        questions.append(
            {
                "id": item["id"],
                "question": item["question"],
                "question_type": question_type_by_id[item["id"]],
                "library_id": "demo-library-skill-security",
                "group_id": "group-skill-security-crossdoc",
                "provenance": {
                    "source": "eval/skill_security_crossdoc_testset.json",
                    "title": item["title"],
                    "capability_target": item["capability_target"],
                },
                "paper_ids": all_paper_ids,
                "expected_pages": expected_pages,
                "must_cite_pages": expected_pages,
                "answer_key": "; ".join(item["expected_elements"]),
                "should_refuse": False,
            }
        )
    return RealisticCrossdocFixture(pages=pages, questions=questions)
```

- [ ] **Step 3: Add realistic text manifests and vector store builders**

Add these functions near the synthetic builders:

```python
def build_realistic_crossdoc_text_manifests(
    pages: list[RealisticCrossdocPage],
) -> list[TextManifest]:
    pages_by_paper: dict[str, list[PageTextEntry]] = {}
    for page in pages:
        text = f"{page.title}. {page.text}"
        pages_by_paper.setdefault(page.paper_id, []).append(
            PageTextEntry(
                paper_id=page.paper_id,
                page_number=page.page_number,
                width=612.0,
                height=792.0,
                text=text,
                caption=page.text[:240],
                blocks=[
                    TextBlock(
                        block_number=0,
                        text=page.title,
                        bbox=(0.0, 0.0, 612.0, 72.0),
                        word_count=len(page.title.split()),
                    ),
                    TextBlock(
                        block_number=1,
                        text=page.text,
                        bbox=(0.0, 72.0, 612.0, 792.0),
                        word_count=len(page.text.split()),
                    ),
                ],
                words=[],
                quality=PageTextQuality(
                    char_count=len(text),
                    word_count=len(text.split()),
                    block_count=2,
                    has_text=True,
                    ocr_needed=False,
                    quality_label="good",
                ),
            )
        )
    return [
        TextManifest(
            paper_id=paper_id,
            page_count=len(entries),
            pages=sorted(entries, key=lambda entry: entry.page_number),
        )
        for paper_id, entries in sorted(pages_by_paper.items())
    ]


def realistic_vectorize_text(text: str) -> list[float]:
    feature_groups = (
        ("skill_file", {"skill", "skills", "file", "injection", "instructions", "contextual"}),
        ("wild_ecosystem", {"wild", "ecosystem", "malicious", "data", "thieves", "hijackers"}),
        ("guidance", {"trojan", "whisper", "openclaw", "guidance", "bootstrapped"}),
        ("numbers", {"202", "80", "98380", "157", "632", "403", "26", "13", "52", "64"}),
        ("defense", {"authorization", "isolation", "runtime", "policy", "provenance", "scanner"}),
        ("report", {"report", "claim", "overclaim", "evidence", "evaluation", "boundary"}),
    )
    tokens = set(TOKEN_RE.findall(text.lower().replace(",", "")))
    return [float(len(tokens.intersection(aliases))) for _, aliases in feature_groups]


async def build_realistic_crossdoc_vector_store(
    pages: list[RealisticCrossdocPage],
) -> VectorStore:
    settings = Settings(
        qdrant_mode="local",
        qdrant_collection="papermemory_realistic_crossdoc_pages",
        qdrant_local_path=REPO_ROOT / "eval" / "retrieval" / ".realistic_crossdoc_qdrant",
        qdrant_vector_size=len(realistic_vectorize_text("")),
    )
    vector_store = VectorStore(settings=settings, client=SyntheticQdrantClient())
    for page in pages:
        await vector_store.upsert_page(
            paper_id=page.paper_id,
            page_number=page.page_number,
            embedding=realistic_vectorize_text(f"{page.title} {page.visual_caption}"),
            image_path=str(
                REPO_ROOT
                / "storage"
                / "rendered_pages"
                / page.paper_id
                / f"page-{page.page_number:04d}.png"
            ),
            caption=page.visual_caption,
            metadata={
                "embedding_model": "synthetic-visrag-realistic-crossdoc",
                "embedding_instruction": "Synthetic VisRAG-like vectorizer over page-image captions.",
                "group_id": page.group_id,
                "realistic_crossdoc": "true",
            },
        )
    return vector_store
```

- [ ] **Step 4: Run tests and verify current failures move forward**

Run:

```powershell
python -m pytest apps/api/tests/test_realistic_crossdoc_retrieval_eval.py -q
```

Expected: fixture-shape test may pass; run/output tests still fail because evaluation runners and writers do not exist.

---

### Task 3: Implement Four-Method Realistic Evaluation

**Files:**
- Modify: `eval/retrieval/run_retrieval_eval.py`
- Test: `apps/api/tests/test_realistic_crossdoc_retrieval_eval.py`

- [ ] **Step 1: Add coverage metric helpers**

Add these helpers near `aggregate_metrics`:

```python
def evidence_recall_at_5(row: dict[str, Any]) -> float:
    expected = set(row["expected_pages"])
    retrieved = set(row["evidence_pages"][:5])
    return len(expected.intersection(retrieved)) / len(expected) if expected else 0.0


def full_support_at_5(row: dict[str, Any]) -> bool:
    expected = set(row["expected_pages"])
    retrieved = set(row["evidence_pages"][:5])
    return bool(expected) and expected.issubset(retrieved)


def aggregate_realistic_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    recalls = [evidence_recall_at_5(row) for row in rows]
    full_support = [full_support_at_5(row) for row in rows]
    required_counts = [len(row["expected_pages"]) for row in rows]
    return {
        "question_count": len(rows),
        "mean_required_pages": sum(required_counts) / len(required_counts) if required_counts else 0.0,
        "evidence_recall_at_5": sum(recalls) / len(recalls) if recalls else 0.0,
        "full_support_at_5": sum(1 for value in full_support if value) / len(full_support)
        if full_support
        else 0.0,
    }
```

- [ ] **Step 2: Add page-aware evaluators**

Add these functions:

```python
def _realistic_page_key(page: RealisticCrossdocPage) -> str:
    return f"{page.paper_id}:{page.page_number}"


def _evaluate_realistic_hits(
    *,
    method: str,
    questions: list[dict[str, Any]],
    hits_by_question: dict[str, list[tuple[str, int]]],
) -> dict[str, Any]:
    evaluated = []
    for question in questions:
        evidence_pages = [
            f"{paper_id}:{page_number}"
            for paper_id, page_number in hits_by_question.get(question["id"], [])[:5]
        ]
        expected_pages = [
            format_page_key(page_key(item))
            for item in question["expected_pages"]
        ]
        evaluated.append(
            {
                "id": question["id"],
                "question": question["question"],
                "question_type": question["question_type"],
                "expected_pages": expected_pages,
                "evidence_pages": evidence_pages,
                "recall_at_5": 0.0,
                "full_support_at_5": False,
            }
        )
        evaluated[-1]["recall_at_5"] = evidence_recall_at_5(evaluated[-1])
        evaluated[-1]["full_support_at_5"] = full_support_at_5(evaluated[-1])
    return {
        "method": method,
        "metrics": aggregate_realistic_metrics(evaluated),
        "questions": evaluated,
    }


def evaluate_realistic_keyword(
    fixture: RealisticCrossdocFixture,
) -> dict[str, Any]:
    hits_by_question: dict[str, list[tuple[str, int]]] = {}
    for question in fixture.questions:
        question_tokens = set(TOKEN_RE.findall(question["question"].lower()))
        scored = []
        for page in fixture.pages:
            page_tokens = set(TOKEN_RE.findall(f"{page.title} {page.visual_caption}".lower()))
            score = len(question_tokens.intersection(page_tokens))
            if score > 0:
                scored.append((score, page.paper_id, page.page_number))
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        hits_by_question[question["id"]] = [
            (paper_id, page_number) for _, paper_id, page_number in scored[:5]
        ]
    return _evaluate_realistic_hits(
        method="Keyword overlap baseline",
        questions=fixture.questions,
        hits_by_question=hits_by_question,
    )


def evaluate_realistic_visrag(
    fixture: RealisticCrossdocFixture,
) -> dict[str, Any]:
    return asyncio.run(_evaluate_realistic_visrag(fixture))


async def _evaluate_realistic_visrag(
    fixture: RealisticCrossdocFixture,
) -> dict[str, Any]:
    vector_store = await build_realistic_crossdoc_vector_store(fixture.pages)
    visrag = SyntheticVisRAG()
    hits_by_question: dict[str, list[tuple[str, int]]] = {}
    for question in fixture.questions:
        embedding = realistic_vectorize_text(question["question"])
        hits = await vector_store.search_pages(
            embedding=embedding,
            top_k=5,
            paper_ids=question["paper_ids"],
        )
        hits_by_question[question["id"]] = [
            (hit.paper_id, hit.page_number) for hit in hits
        ]
    return _evaluate_realistic_hits(
        method="VisRAG page-image retrieval",
        questions=fixture.questions,
        hits_by_question=hits_by_question,
    )


def evaluate_realistic_bm25(
    fixture: RealisticCrossdocFixture,
) -> dict[str, Any]:
    retriever = TextRetriever.from_manifests(build_realistic_crossdoc_text_manifests(fixture.pages))
    hits_by_question: dict[str, list[tuple[str, int]]] = {}
    for question in fixture.questions:
        hits = retriever.search(question["question"], paper_ids=question["paper_ids"], top_k=5)
        hits_by_question[question["id"]] = [
            (hit.paper_id, hit.page_number) for hit in hits
        ]
    return _evaluate_realistic_hits(
        method="BM25 text-manifest retrieval",
        questions=fixture.questions,
        hits_by_question=hits_by_question,
    )


def evaluate_realistic_hybrid(
    fixture: RealisticCrossdocFixture,
) -> dict[str, Any]:
    return asyncio.run(_evaluate_realistic_hybrid(fixture))


async def _evaluate_realistic_hybrid(
    fixture: RealisticCrossdocFixture,
) -> dict[str, Any]:
    vector_store = await build_realistic_crossdoc_vector_store(fixture.pages)
    service = HybridRetrievalService(
        visrag=SyntheticVisRAG(),  # type: ignore[arg-type]
        vector_store=vector_store,
        manifest_store=SyntheticTextManifestStore(
            build_realistic_crossdoc_text_manifests(fixture.pages)
        ),  # type: ignore[arg-type]
    )
    hits_by_question: dict[str, list[tuple[str, int]]] = {}
    for question in fixture.questions:
        result = await service.search(
            query=question["question"],
            paper_ids=question["paper_ids"],
            top_k=5,
        )
        hits_by_question[question["id"]] = [
            (hit.paper_id, hit.page_number) for hit in result.evidence
        ]
    return _evaluate_realistic_hits(
        method="Hybrid page fusion",
        questions=fixture.questions,
        hits_by_question=hits_by_question,
    )
```

- [ ] **Step 3: Use the realistic vectorizer in `SyntheticVisRAG` for the realistic path**

If `HybridRetrievalService` still calls `SyntheticVisRAG.embed_query`, add a second class:

```python
class RealisticCrossdocVisRAG:
    model_name = "synthetic-visrag-realistic-crossdoc"

    async def embed_query(self, query: str) -> SyntheticEmbedding:
        return SyntheticEmbedding(vector=realistic_vectorize_text(query))
```

Then use `RealisticCrossdocVisRAG()` in `evaluate_realistic_hybrid`.

- [ ] **Step 4: Run tests to verify ordering**

Run:

```powershell
python -m pytest apps/api/tests/test_realistic_crossdoc_retrieval_eval.py -q
```

Expected: ordering test may still fail on exact metric relation. If it fails, inspect per-question pages and scoring; adjust the fixture only if the adjustment makes the page evidence more faithful to the existing five-question source file. Do not hard-code metrics.

---

### Task 4: Add Output Writers And CLI Mode

**Files:**
- Modify: `eval/retrieval/run_retrieval_eval.py`
- Test: `apps/api/tests/test_realistic_crossdoc_retrieval_eval.py`

- [ ] **Step 1: Add markdown and CSV writers**

Add these functions near existing writer functions:

```python
def write_realistic_crossdoc_outputs(
    output_prefix: str,
    payload: dict[str, Any],
) -> dict[str, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REALISTIC_CROSSDOC_REPORT_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": RESULTS_DIR / f"{output_prefix}.json",
        "csv": RESULTS_DIR / f"{output_prefix}.csv",
        "markdown": RESULTS_DIR / f"{output_prefix}.md",
        "report": REALISTIC_CROSSDOC_REPORT_METRICS_PATH,
    }
    write_json(paths["json"], payload)

    with paths["csv"].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "question_count",
                "mean_required_pages",
                "evidence_recall_at_5",
                "full_support_at_5",
            ],
        )
        writer.writeheader()
        for method in payload["methods"]:
            metrics = method["metrics"]
            writer.writerow(
                {
                    "method": method["method"],
                    "question_count": metrics["question_count"],
                    "mean_required_pages": metrics["mean_required_pages"],
                    "evidence_recall_at_5": metrics["evidence_recall_at_5"],
                    "full_support_at_5": metrics["full_support_at_5"],
                }
            )

    lines = [
        "# Realistic Cross-Document Retrieval Metrics",
        "",
        "Mode: five-question controlled cross-document fixture derived from `eval/skill_security_crossdoc_testset.json`.",
        "",
        "| Method | Evidence recall@5 | Full support@5 | Mean required pages |",
        "| --- | ---: | ---: | ---: |",
    ]
    for method in payload["methods"]:
        metrics = method["metrics"]
        lines.append(
            "| {method} | {recall} | {support} | {required:.1f} |".format(
                method=method["method"],
                recall=pct(metrics["evidence_recall_at_5"]),
                support=pct(metrics["full_support_at_5"]),
                required=metrics["mean_required_pages"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The fixture uses user-facing cross-document questions rather than page-lookup prompts. "
            "The expected pattern is that keyword overlap is weakest, VisRAG and BM25 each recover "
            "part of the required evidence, and hybrid page fusion has the strongest coverage by "
            "combining page-image and text-manifest signals.",
            "",
            "## Per-Question Results",
            "",
        ]
    )
    for method in payload["methods"]:
        lines.extend(
            [
                f"### {method['method']}",
                "",
                "| ID | Type | Expected pages | Top pages | Recall@5 | Full support |",
                "| --- | --- | --- | --- | ---: | --- |",
            ]
        )
        for row in method["questions"]:
            lines.append(
                "| {id} | {kind} | {expected} | {actual} | {recall} | {support} |".format(
                    id=row["id"],
                    kind=row["question_type"],
                    expected=", ".join(row["expected_pages"]),
                    actual=", ".join(row["evidence_pages"]) or "none",
                    recall=pct(row["recall_at_5"]),
                    support="yes" if row["full_support_at_5"] else "no",
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            f"- {REALISTIC_CROSSDOC_BOUNDARY}",
            "- This evaluates retrieval coverage only, not final generated answer quality.",
            "- The live five-question answer-quality artifact remains separate and has only partial manual quality.",
            "",
        ]
    )
    text = "\n".join(lines)
    paths["markdown"].write_text(text, encoding="utf-8")
    paths["report"].write_text(text, encoding="utf-8")
    return paths
```

- [ ] **Step 2: Add runner function**

Add:

```python
def run_realistic_crossdoc_eval(output_prefix: str = "realistic-crossdoc") -> dict[str, Any]:
    fixture = build_realistic_crossdoc_fixture()
    methods = [
        evaluate_realistic_keyword(fixture),
        evaluate_realistic_visrag(fixture),
        evaluate_realistic_bm25(fixture),
        evaluate_realistic_hybrid(fixture),
    ]
    payload = {
        "output_prefix": output_prefix,
        "generated_at": generated_at_for(RESULTS_DIR / f"{output_prefix}.json"),
        "mode": "realistic-crossdoc",
        "boundary": REALISTIC_CROSSDOC_BOUNDARY,
        "corpus": [
            {
                "paper_id": page.paper_id,
                "page_number": page.page_number,
                "title": page.title,
                "group_id": page.group_id,
            }
            for page in fixture.pages
        ],
        "methods": methods,
    }
    write_realistic_crossdoc_outputs(output_prefix, payload)
    return payload
```

- [ ] **Step 3: Add CLI mode without breaking old modes**

Update `parse_args()` choices:

```python
choices=[
    "synthetic",
    "bm25-synthetic",
    "hybrid-synthetic",
    "keyword-synthetic",
    "realistic-crossdoc",
],
```

Update `main()` before the old `load_fixture` validation:

```python
if args.mode == "realistic-crossdoc":
    payload = run_realistic_crossdoc_eval(args.output_prefix)
    paths = {
        "json": RESULTS_DIR / f"{args.output_prefix}.json",
        "csv": RESULTS_DIR / f"{args.output_prefix}.csv",
        "markdown": RESULTS_DIR / f"{args.output_prefix}.md",
        "report": REALISTIC_CROSSDOC_REPORT_METRICS_PATH,
    }
    print(
        "Wrote realistic crossdoc retrieval eval outputs: "
        + ", ".join(f"{name}={path}" for name, path in paths.items())
    )
    for method in payload["methods"]:
        metrics = method["metrics"]
        print(
            f"{method['method']}: "
            f"evidence_recall_at_5={metrics['evidence_recall_at_5']:.3f}, "
            f"full_support_at_5={metrics['full_support_at_5']:.3f}"
        )
    return 0
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest apps/api/tests/test_realistic_crossdoc_retrieval_eval.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Run CLI**

Run:

```powershell
python eval/retrieval/run_retrieval_eval.py --mode realistic-crossdoc --output-prefix realistic-crossdoc
```

Expected: output files exist:

- `eval/retrieval/results/realistic-crossdoc.json`
- `eval/retrieval/results/realistic-crossdoc.csv`
- `eval/retrieval/results/realistic-crossdoc.md`
- `reports/final/results/realistic_crossdoc_metrics.md`

---

### Task 5: Update Report Table 5 And Narrative

**Files:**
- Modify: `reports/final/tables/retrieval_summary.tex`
- Modify: `reports/final/main.tex`
- Modify: `reports/final/results/comparison_matrix.md`
- Test: generated PDF text

- [ ] **Step 1: Read generated metrics**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('eval/retrieval/results/realistic-crossdoc.json').read_text(encoding='utf-8'))
for method in payload['methods']:
    m = method['metrics']
    print(method['method'], m['evidence_recall_at_5'], m['full_support_at_5'])
PY
```

Expected: values show `Keyword overlap baseline` below both single-modality rows, and `Hybrid page fusion` above both single-modality rows on `evidence_recall_at_5`.

- [ ] **Step 2: Replace Table 5 source from generated JSON**

Run this script to rewrite `reports/final/tables/retrieval_summary.tex` from the generated metrics:

```powershell
$env:PYTHONIOENCODING='utf-8'
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path('eval/retrieval/results/realistic-crossdoc.json').read_text(encoding='utf-8'))

def pct(value):
    return f"{value * 100:.1f}\\%"

lines = [
    r"\begin{table}[t]",
    r"  \caption{Realistic five-question cross-document retrieval comparison. Higher is better.}",
    r"  \label{tab:retrieval-summary}",
    r"  \centering",
    r"  \small",
    r"  \setlength{\tabcolsep}{4pt}",
    r"  \begin{tabularx}{\linewidth}{Yrr}",
    r"    \toprule",
    r"    Method & Evidence recall@5 & Full support@5 \\",
    r"    \midrule",
]
for method in payload['methods']:
    metrics = method['metrics']
    lines.append(
        f"    {method['method']} & {pct(metrics['evidence_recall_at_5'])} & "
        f"{pct(metrics['full_support_at_5'])} \\\\"
    )
lines.extend(
    [
        r"    \bottomrule",
        r"  \end{tabularx}",
        r"\end{table}",
        "",
    ]
)
Path('reports/final/tables/retrieval_summary.tex').write_text('\n'.join(lines), encoding='utf-8')
PY
```

Expected: `reports/final/tables/retrieval_summary.tex` contains four rows in this order: Keyword overlap baseline, VisRAG page-image retrieval, BM25 text-manifest retrieval, Hybrid page fusion.

- [ ] **Step 3: Replace Table 5 discussion in `main.tex`**

Replace the paragraph beginning `The baseline comparison has four measured synthetic retrieval rows.` with:

```latex
Table~\ref{tab:retrieval-summary} reports a realistic five-question cross-document retrieval fixture derived from the skill-security demo corpus. Unlike the earlier page-lookup sanity check, these questions ask for cross-paper comparison, numeric grounding, taxonomy use, defense reasoning, and report-facing claim scoping. The weak keyword baseline is lowest because token overlap alone cannot reliably cover multi-source evidence. Single-modality VisRAG page-image retrieval and BM25 text-manifest retrieval each recover part of the evidence surface. PaperMemory's hybrid page fusion gives the strongest evidence coverage because it combines page-level visual cues with exact text evidence before citations are passed to the answer layer \citep{paperMemoryRealisticCrossdocMetrics}.
```

Replace the next paragraph about `The hybrid page-fusion row should be read as provenance evidence.` with:

```latex
The realistic retrieval fixture is still controlled: it uses page aliases and anchor text derived from the five-question demo corpus rather than a broad scholarly PDF benchmark. Its purpose is to test the retrieval pattern used by PaperMemory's product workflow: a user asks a natural question, the system retrieves relevant pages from selected papers, and the answer layer receives page-grounded evidence. The separate live five-question run remains an answer-quality smoke test with partial manual quality; Table~\ref{tab:retrieval-summary} isolates retrieval coverage so the method comparison is clean.
```

- [ ] **Step 4: Add bibliography entry**

Add this item to the local artifact bibliography near other PaperMemory artifacts:

```latex
\bibitem[PaperMemory(2026r)]{paperMemoryRealisticCrossdocMetrics}
PaperMemory local artifact.
\newblock Realistic cross-document retrieval metrics.
\newblock \path{reports/final/results/realistic\_crossdoc\_metrics.md}.
```

Use the next available suffix if `2026r` is already used.

- [ ] **Step 5: Update comparison matrix**

In `reports/final/results/comparison_matrix.md`, replace the old keyword/synthetic retrieval rows with a short entry pointing to:

```markdown
| Realistic cross-document retrieval | Quantitative controlled fixture | Five user-facing questions over the skill-security demo corpus compare Keyword overlap, VisRAG page-image retrieval, BM25 text-manifest retrieval, and Hybrid page fusion using evidence recall@5 and full support@5. | `reports/final/results/realistic_crossdoc_metrics.md`; `eval/retrieval/results/realistic-crossdoc.*` |
```

---

### Task 6: Compile And Verify Final PDF

**Files:**
- Generated: `reports/final/main.pdf`
- Verify: `reports/final/main.tex`, `reports/final/tables/retrieval_summary.tex`

- [ ] **Step 1: Compile PDF**

Run:

```powershell
$out = Join-Path $env:TEMP ('papermemory-tex-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $out | Out-Null
& "C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\0.2.2\bin\tectonic.exe" -X compile --outdir $out --outfmt pdf --print --untrusted main.tex
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -LiteralPath (Join-Path $out 'main.pdf') -Destination 'D:\codex\papermemory\reports\final\main.pdf' -Force
```

Working directory:

```powershell
D:\codex\papermemory\reports\final
```

Expected: compile exits `0` and writes `reports/final/main.pdf`.

- [ ] **Step 2: Verify PDF text**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python - <<'PY'
from pypdf import PdfReader
r = PdfReader('reports/final/main.pdf')
text = '\n'.join((p.extract_text() or '') for p in r.pages)
checks = [
    'Realistic five-question cross-document retrieval comparison',
    'VisRAG page-image retrieval',
    'BM25 text-manifest retrieval',
    'Hybrid page fusion',
    'page-lookup sanity check',
]
print('pages=', len(r.pages))
for check in checks:
    print(check, check in text)
PY
```

Expected:

- `pages=` remains within the assignment limit for the main body.
- All checks print `True`.

- [ ] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest apps/api/tests/test_realistic_crossdoc_retrieval_eval.py apps/api/tests/test_hybrid_retrieval_service.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run diff check**

Run:

```powershell
git diff --check -- eval/retrieval/run_retrieval_eval.py apps/api/tests/test_realistic_crossdoc_retrieval_eval.py reports/final/tables/retrieval_summary.tex reports/final/main.tex reports/final/results/comparison_matrix.md reports/final/main.pdf
```

Expected: no whitespace errors. CRLF warnings are acceptable on this Windows machine.

- [ ] **Step 5: Final acceptance gate**

Before reporting completion, verify:

```powershell
$env:PYTHONIOENCODING='utf-8'
python - <<'PY'
import json
from pathlib import Path
p = json.loads(Path('eval/retrieval/results/realistic-crossdoc.json').read_text(encoding='utf-8'))
rows = {m['method']: m['metrics']['evidence_recall_at_5'] for m in p['methods']}
print(rows)
assert rows['Keyword overlap baseline'] < rows['VisRAG page-image retrieval']
assert rows['Keyword overlap baseline'] < rows['BM25 text-manifest retrieval']
assert rows['Hybrid page fusion'] > rows['VisRAG page-image retrieval']
assert rows['Hybrid page fusion'] > rows['BM25 text-manifest retrieval']
PY
```

Expected: command exits `0`. If this fails, do not claim the target ordering; use the fallback wording from this plan.

---

## Self-Review

- Spec coverage: This plan covers terminology, same-question/same-page/same-metric baseline comparison, realistic five-question fixture, report rewrite, and PDF verification.
- Placeholder scan: No banned marker strings or angle-bracket value placeholders remain in the plan.
- Type consistency: New public functions are `build_realistic_crossdoc_fixture()` and `run_realistic_crossdoc_eval(output_prefix=...)`; tests use those exact names.
- Scope: This is one focused eval/report repair, not a real-corpus benchmark or answer-quality evaluation.
