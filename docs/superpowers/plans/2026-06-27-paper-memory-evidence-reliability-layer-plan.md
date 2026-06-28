# PaperMemory Evidence Reliability Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a general Evidence Reliability Layer that makes PaperMemory's agent more robust across arbitrary multi-paper questions by planning evidence requirements, checking coverage, verifying claims, and exposing calibrated answer quality.

**Architecture:** Add small, typed backend services around the existing evidence packet and bounded orchestrator instead of replacing the retrieval stack. The layer should classify question intent, derive a generic evidence requirement contract, use coverage gates to drive bounded targeted retries, verify final claims against accepted evidence, and return a public reliability report in `/chat` responses and SSE done frames.

**Tech Stack:** FastAPI, Pydantic v2, existing `EvidencePacket` / `AgentTrace` schemas, existing page-level VisRAG + BM25 hybrid retrieval, pytest, TypeScript web API types.

---

## Scope And Efficiency Rules

- This plan must not hardcode facts, page numbers, paper IDs, or expected answers from the three skill-security PDFs.
- Prefer deterministic heuristics and typed contracts first; use LLM calls only where the existing orchestrator already uses them.
- Keep write sets small and reviewable. Add focused modules instead of expanding `chat_service.py` with large new logic.
- Preserve backwards compatibility: existing `/chat` clients should still work if they ignore the new `reliability_report` field.
- Do not add LangGraph, CrewAI, cross-encoder rerankers, OCR, table parsers, or new external services in this node. Those are future upgrades after the reliability contract proves useful.
- Treat malicious or adversarial PDF text as evidence only. Planner output remains an untrusted hint.
- The implementation is successful only if it improves generic reliability signals on synthetic and live-style tests without degrading existing evidence packet, streaming, robustness, or prompt-injection tests.

## File Map

Create:

- `apps/api/app/schemas/reliability.py` — Pydantic contract for question intent, evidence requirements, coverage reports, claim support, and answer-quality status.
- `apps/api/app/services/evidence_requirement_service.py` — deterministic intent classifier and requirement planner.
- `apps/api/app/services/evidence_coverage_service.py` — generic coverage gate over accepted `EvidencePacket` units.
- `apps/api/app/services/answer_claim_verifier.py` — conservative post-generation claim verifier.
- `apps/api/tests/test_evidence_requirement_service.py` — unit tests for generic intent and requirement planning.
- `apps/api/tests/test_evidence_coverage_service.py` — unit tests for paper, numeric, taxonomy, and quote/claim coverage.
- `apps/api/tests/test_answer_claim_verifier.py` — unit tests for supported, unsupported, numeric, and overclaim checks.
- `apps/api/tests/test_chat_reliability_layer.py` — integration tests for `/chat` response reliability metadata.
- `eval/evidence_reliability_general_testset.json` — small generic test set with domain-neutral cases.
- `reports/final/results/evidence_reliability_layer.md` — report-facing summary of the new capability and claim boundaries.

Modify:

- `apps/api/app/schemas/chat.py` — add optional request flag and response `reliability_report`.
- `apps/api/app/schemas/agent_trace.py` — add safe trace state for `coverage_check`.
- `apps/api/app/services/research_orchestrator.py` — evaluate coverage between passes and use generic targeted retry queries.
- `apps/api/app/services/chat_service.py` — wire requirement planner, coverage report, and claim verifier around generation.
- `apps/api/app/services/context_builder.py` — add evidence requirement and reliability instructions to generation prompts without domain-specific facts.
- `apps/api/app/routers/chat.py` — include reliability metadata in streaming frames.
- `apps/web/lib/types.ts` — add optional reliability report TypeScript types.
- `apps/web/lib/api.ts` — preserve optional reliability report in streamed final response.
- `apps/web/lib/use-chat-session.ts` — store reliability report on assistant messages if the local state type supports it.
- `apps/web/components/evidence-panel.tsx` or `apps/web/components/chat-panel.tsx` — display a compact reliability badge only when present.
- Existing tests touching `ChatResponse`, streaming done frames, and agent traces.

---

### Task 1: Add Reliability Schemas

**Files:**
- Create: `apps/api/app/schemas/reliability.py`
- Create: `apps/api/tests/test_evidence_requirement_service.py`
- Modify later tasks: `apps/api/app/schemas/chat.py`

- [ ] **Step 1: Write schema tests for serializable generic contracts**

Add these tests to `apps/api/tests/test_evidence_requirement_service.py`:

```python
from app.schemas.reliability import (
    AnswerQualityStatus,
    ClaimSupport,
    EvidenceCoverageReport,
    EvidenceRequirement,
    QuestionIntent,
)


def test_reliability_schema_serializes_generic_requirement() -> None:
    requirement = EvidenceRequirement(
        intent=QuestionIntent(intent_type="numeric_grounding", confidence=0.9),
        required_claim_types=["number", "comparison"],
        requires_multi_paper_coverage=True,
        minimum_relevant_pages_per_paper=1,
        must_verify_numeric_claims=True,
        allow_inference="labeled_only",
    )

    payload = requirement.model_dump(mode="json")

    assert payload["intent"]["intent_type"] == "numeric_grounding"
    assert payload["required_claim_types"] == ["number", "comparison"]
    assert payload["allow_inference"] == "labeled_only"


def test_coverage_report_computes_quality_status_from_missing_requirements() -> None:
    report = EvidenceCoverageReport(
        requirement_id="er-test",
        status="partial",
        covered_paper_ids=["paper-a"],
        missing_paper_ids=["paper-b"],
        covered_claim_types=["number"],
        missing_claim_types=["comparison"],
        targeted_queries=["paper-b comparison numeric evidence"],
        limits=["Missing required paper coverage."],
    )

    assert report.status == "partial"
    assert report.targeted_queries == ["paper-b comparison numeric evidence"]


def test_claim_support_marks_unsupported_claims_without_hiding_text() -> None:
    support = ClaimSupport(
        claim_text="The system detects all malicious skills.",
        support_status="unsupported",
        evidence_ids=[],
        reason="No accepted evidence supports universal detection.",
    )

    assert support.support_status == "unsupported"
    assert support.evidence_ids == []
    assert "universal detection" in support.reason
    assert AnswerQualityStatus("partial") == "partial"
```

- [ ] **Step 2: Run the schema tests and verify they fail**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_requirement_service.py -q
```

Expected: import failure for `app.schemas.reliability`.

- [ ] **Step 3: Create reliability schema module**

Create `apps/api/app/schemas/reliability.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QuestionIntentType = Literal[
    "numeric_grounding",
    "cross_document_comparison",
    "taxonomy_classification",
    "method_or_result_extraction",
    "defense_or_recommendation",
    "claim_boundary",
    "general_paper_qa",
]

ClaimType = Literal[
    "number",
    "comparison",
    "taxonomy",
    "method",
    "result",
    "recommendation",
    "limitation",
    "safety_boundary",
]

InferencePolicy = Literal["none", "labeled_only", "allowed"]
CoverageStatus = Literal["strong", "partial", "insufficient"]
AnswerQualityStatus = Literal["strong", "partial", "insufficient"]
ClaimSupportStatus = Literal["supported", "partially_supported", "unsupported"]


class QuestionIntent(BaseModel):
    intent_type: QuestionIntentType
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = Field(default=None, max_length=240)


class EvidenceRequirement(BaseModel):
    requirement_id: str = "er-default"
    intent: QuestionIntent
    required_claim_types: list[ClaimType] = Field(default_factory=list)
    requires_multi_paper_coverage: bool = False
    minimum_relevant_pages_per_paper: int = Field(default=0, ge=0, le=5)
    must_verify_numeric_claims: bool = False
    allow_inference: InferencePolicy = "labeled_only"
    max_targeted_queries: int = Field(default=4, ge=0, le=8)


class EvidenceCoverageReport(BaseModel):
    requirement_id: str
    status: CoverageStatus
    covered_paper_ids: list[str] = Field(default_factory=list)
    missing_paper_ids: list[str] = Field(default_factory=list)
    covered_claim_types: list[ClaimType] = Field(default_factory=list)
    missing_claim_types: list[ClaimType] = Field(default_factory=list)
    matched_numbers: list[str] = Field(default_factory=list)
    missing_numbers: list[str] = Field(default_factory=list)
    targeted_queries: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)


class ClaimSupport(BaseModel):
    claim_text: str = Field(max_length=800)
    support_status: ClaimSupportStatus
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str = Field(max_length=400)


class AnswerReliabilityReport(BaseModel):
    status: AnswerQualityStatus
    requirement: EvidenceRequirement
    coverage: EvidenceCoverageReport
    claims: list[ClaimSupport] = Field(default_factory=list)
    unsupported_claim_count: int = 0
    limits: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run the schema tests and verify they pass**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_requirement_service.py -q
```

Expected: `3 passed`.

---

### Task 2: Build Generic Evidence Requirement Planner

**Files:**
- Modify: `apps/api/tests/test_evidence_requirement_service.py`
- Create: `apps/api/app/services/evidence_requirement_service.py`

- [ ] **Step 1: Add deterministic planner tests**

Append to `apps/api/tests/test_evidence_requirement_service.py`:

```python
from app.services.evidence_requirement_service import EvidenceRequirementService


def test_requirement_planner_detects_numeric_cross_document_questions() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="Which concrete numbers across these papers show the threat is real?",
        paper_ids=["p1", "p2", "p3"],
    )

    assert requirement.intent.intent_type == "numeric_grounding"
    assert requirement.requires_multi_paper_coverage is True
    assert requirement.minimum_relevant_pages_per_paper == 1
    assert requirement.must_verify_numeric_claims is True
    assert "number" in requirement.required_claim_types
    assert "comparison" in requirement.required_claim_types


def test_requirement_planner_detects_taxonomy_without_paper_specific_terms() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="Classify this risk using the papers and explain which source supports each label.",
        paper_ids=["p1", "p2"],
    )

    assert requirement.intent.intent_type == "taxonomy_classification"
    assert requirement.requires_multi_paper_coverage is True
    assert "taxonomy" in requirement.required_claim_types
    assert requirement.allow_inference == "labeled_only"


def test_requirement_planner_detects_claim_boundary_report_questions() -> None:
    service = EvidenceRequirementService()

    requirement = service.plan(
        question="What should our report claim and what should it not overclaim?",
        paper_ids=["p1"],
    )

    assert requirement.intent.intent_type == "claim_boundary"
    assert "safety_boundary" in requirement.required_claim_types
    assert requirement.allow_inference == "labeled_only"
```

- [ ] **Step 2: Run the planner tests and verify they fail**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_requirement_service.py -q
```

Expected: import failure for `EvidenceRequirementService`.

- [ ] **Step 3: Implement deterministic generic planner**

Create `apps/api/app/services/evidence_requirement_service.py`:

```python
from __future__ import annotations

import hashlib
import re

from app.schemas.reliability import EvidenceRequirement, QuestionIntent

_NUMERIC_RE = re.compile(r"\b(number|numbers|rate|rates|percent|percentage|scale|cost|token|tokens|how much|compare)\b", re.I)
_TAXONOMY_RE = re.compile(r"\b(classify|classification|taxonomy|label|category|archetype|risk type)\b", re.I)
_DEFENSE_RE = re.compile(r"\b(defense|defence|mitigation|recommendation|secure|robust|safety|policy)\b", re.I)
_BOUNDARY_RE = re.compile(r"\b(report|claim|overclaim|limitation|should not|cannot support|boundary)\b", re.I)
_METHOD_RE = re.compile(r"\b(method|approach|experiment|result|finding|ablation|evaluation)\b", re.I)
_CROSS_DOC_RE = re.compile(r"\b(across|compare|between|among|papers|documents|sources)\b", re.I)


class EvidenceRequirementService:
    """Plans generic evidence requirements from a user question and paper scope."""

    def plan(self, *, question: str, paper_ids: list[str] | None) -> EvidenceRequirement:
        normalized = " ".join(question.split())
        paper_count = len(paper_ids or [])
        intent = self._intent_for(normalized)
        claim_types = self._claim_types_for(normalized, intent.intent_type)
        multi_paper = paper_count > 1 and (
            bool(_CROSS_DOC_RE.search(normalized))
            or intent.intent_type in {"numeric_grounding", "cross_document_comparison", "taxonomy_classification"}
        )
        return EvidenceRequirement(
            requirement_id=self._requirement_id(normalized, paper_ids or []),
            intent=intent,
            required_claim_types=claim_types,
            requires_multi_paper_coverage=multi_paper,
            minimum_relevant_pages_per_paper=1 if multi_paper else 0,
            must_verify_numeric_claims="number" in claim_types,
            allow_inference="labeled_only",
            max_targeted_queries=4,
        )

    def _intent_for(self, question: str) -> QuestionIntent:
        if _BOUNDARY_RE.search(question):
            return QuestionIntent(intent_type="claim_boundary", confidence=0.85)
        if _NUMERIC_RE.search(question):
            return QuestionIntent(intent_type="numeric_grounding", confidence=0.85)
        if _TAXONOMY_RE.search(question):
            return QuestionIntent(intent_type="taxonomy_classification", confidence=0.8)
        if _DEFENSE_RE.search(question):
            return QuestionIntent(intent_type="defense_or_recommendation", confidence=0.75)
        if _METHOD_RE.search(question):
            return QuestionIntent(intent_type="method_or_result_extraction", confidence=0.7)
        if _CROSS_DOC_RE.search(question):
            return QuestionIntent(intent_type="cross_document_comparison", confidence=0.7)
        return QuestionIntent(intent_type="general_paper_qa", confidence=0.55)

    @staticmethod
    def _claim_types_for(question: str, intent_type: str) -> list[str]:
        claim_types: list[str] = []
        if _NUMERIC_RE.search(question) or intent_type == "numeric_grounding":
            claim_types.extend(["number", "comparison"])
        if intent_type == "taxonomy_classification":
            claim_types.append("taxonomy")
        if intent_type in {"method_or_result_extraction", "numeric_grounding"}:
            claim_types.extend(["method", "result"])
        if intent_type == "defense_or_recommendation":
            claim_types.append("recommendation")
        if intent_type == "claim_boundary":
            claim_types.extend(["recommendation", "safety_boundary", "limitation"])
        if not claim_types:
            claim_types.append("result")
        return list(dict.fromkeys(claim_types))

    @staticmethod
    def _requirement_id(question: str, paper_ids: list[str]) -> str:
        payload = "|".join([question.lower(), *paper_ids])
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"er-{digest}"
```

- [ ] **Step 4: Run planner tests**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_requirement_service.py -q
```

Expected: all tests in that file pass.

---

### Task 3: Add Generic Evidence Coverage Gate

**Files:**
- Create: `apps/api/app/services/evidence_coverage_service.py`
- Create: `apps/api/tests/test_evidence_coverage_service.py`

- [ ] **Step 1: Write coverage tests**

Create `apps/api/tests/test_evidence_coverage_service.py`:

```python
from app.schemas.evidence import EvidenceCitation, EvidencePacket, EvidenceUnit
from app.schemas.reliability import EvidenceRequirement, QuestionIntent
from app.services.evidence_coverage_service import EvidenceCoverageService


def _unit(paper_id: str, page: int, caption: str, evidence_id: str | None = None) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=evidence_id or f"ev-{paper_id}-{page}",
        paper_id=paper_id,
        page_number=page,
        source="hybrid_page",
        score=0.8,
        caption=caption,
        validation_state="validated",
    )


def _packet(units: list[EvidenceUnit]) -> EvidencePacket:
    return EvidencePacket(
        packet_id="ep-test",
        query="test",
        paper_scope=["p1", "p2"],
        units=units,
        citations=[
            EvidenceCitation(
                evidence_id=unit.evidence_id,
                paper_id=unit.paper_id,
                page_number=unit.page_number,
                label=f"{unit.paper_id} p.{unit.page_number}",
            )
            for unit in units
        ],
    )


def _numeric_requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="er-numeric",
        intent=QuestionIntent(intent_type="numeric_grounding", confidence=0.9),
        required_claim_types=["number", "comparison"],
        requires_multi_paper_coverage=True,
        minimum_relevant_pages_per_paper=1,
        must_verify_numeric_claims=True,
    )


def test_coverage_gate_detects_missing_paper_for_multi_paper_question() -> None:
    service = EvidenceCoverageService()
    report = service.evaluate(
        question="Compare the reported numbers across papers.",
        paper_ids=["p1", "p2"],
        requirement=_numeric_requirement(),
        packet=_packet([_unit("p1", 1, "Accuracy is 80%.")]),
    )

    assert report.status == "partial"
    assert report.covered_paper_ids == ["p1"]
    assert report.missing_paper_ids == ["p2"]
    assert report.targeted_queries == ["p2 reported numbers comparison evidence"]


def test_coverage_gate_matches_numbers_from_question_and_evidence() -> None:
    service = EvidenceCoverageService()
    report = service.evaluate(
        question="Does the evidence support 80% and 94%?",
        paper_ids=["p1", "p2"],
        requirement=_numeric_requirement(),
        packet=_packet([
            _unit("p1", 1, "The reported success rate is 80%."),
            _unit("p2", 1, "The scanner evasion rate is 94%."),
        ]),
    )

    assert report.status == "strong"
    assert report.matched_numbers == ["80%", "94%"]
    assert report.missing_numbers == []
    assert report.targeted_queries == []


def test_coverage_gate_detects_missing_numeric_claim_type() -> None:
    service = EvidenceCoverageService()
    report = service.evaluate(
        question="Which numbers show the system works?",
        paper_ids=["p1"],
        requirement=_numeric_requirement().model_copy(
            update={"requires_multi_paper_coverage": False, "minimum_relevant_pages_per_paper": 0}
        ),
        packet=_packet([_unit("p1", 1, "The method is described qualitatively.")]),
    )

    assert report.status == "partial"
    assert "number" in report.missing_claim_types
    assert report.targeted_queries == ["numbers result evidence"]
```

- [ ] **Step 2: Run coverage tests and verify they fail**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_coverage_service.py -q
```

Expected: import failure for `EvidenceCoverageService`.

- [ ] **Step 3: Implement coverage service**

Create `apps/api/app/services/evidence_coverage_service.py`:

```python
from __future__ import annotations

import re

from app.schemas.evidence import EvidencePacket
from app.schemas.reliability import EvidenceCoverageReport, EvidenceRequirement

_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*%?|\b\d+\s*/\s*\d+\b")
_TAXONOMY_RE = re.compile(r"\b(taxonomy|class|category|label|archetype|type)\b", re.I)
_RECOMMENDATION_RE = re.compile(r"\b(recommend|defense|defence|mitigation|should|policy|enforce|isolation)\b", re.I)
_LIMITATION_RE = re.compile(r"\b(limit|limitation|cannot|not prove|not support|insufficient|missing)\b", re.I)


class EvidenceCoverageService:
    """Checks whether accepted evidence satisfies a generic requirement contract."""

    def evaluate(
        self,
        *,
        question: str,
        paper_ids: list[str] | None,
        requirement: EvidenceRequirement,
        packet: EvidencePacket | None,
    ) -> EvidenceCoverageReport:
        units = list(packet.units if packet is not None else [])
        scoped_ids = list(paper_ids or packet.paper_scope if packet is not None and packet.paper_scope else paper_ids or [])
        evidence_text = "\n".join(" ".join(filter(None, [unit.title, unit.caption])) for unit in units)

        covered_papers = sorted({unit.paper_id for unit in units if unit.paper_id in set(scoped_ids)})
        missing_papers: list[str] = []
        if requirement.requires_multi_paper_coverage:
            missing_papers = [paper_id for paper_id in scoped_ids if paper_id not in covered_papers]

        question_numbers = _ordered_unique(_NUMBER_RE.findall(question))
        evidence_numbers = _ordered_unique(_NUMBER_RE.findall(evidence_text))
        matched_numbers = [number for number in question_numbers if number in evidence_numbers]
        missing_numbers = [number for number in question_numbers if number not in evidence_numbers]

        covered_claim_types = self._covered_claim_types(evidence_text, evidence_numbers)
        missing_claim_types = [
            claim_type
            for claim_type in requirement.required_claim_types
            if claim_type not in covered_claim_types
        ]
        if requirement.must_verify_numeric_claims and "number" in requirement.required_claim_types and not evidence_numbers:
            if "number" not in missing_claim_types:
                missing_claim_types.append("number")

        limits: list[str] = []
        if missing_papers:
            limits.append("Missing required paper coverage.")
        if missing_numbers:
            limits.append("Missing required numeric evidence from accepted packet.")
        if missing_claim_types:
            limits.append("Missing required claim-type coverage.")

        targeted_queries = self._targeted_queries(
            missing_papers=missing_papers,
            missing_claim_types=missing_claim_types,
            requirement=requirement,
        )
        status = "strong" if not limits else "partial" if units else "insufficient"
        return EvidenceCoverageReport(
            requirement_id=requirement.requirement_id,
            status=status,
            covered_paper_ids=covered_papers,
            missing_paper_ids=missing_papers,
            covered_claim_types=covered_claim_types,
            missing_claim_types=missing_claim_types,
            matched_numbers=matched_numbers,
            missing_numbers=missing_numbers,
            targeted_queries=targeted_queries[: requirement.max_targeted_queries],
            limits=limits,
        )

    @staticmethod
    def _covered_claim_types(evidence_text: str, evidence_numbers: list[str]) -> list[str]:
        covered: list[str] = []
        if evidence_numbers:
            covered.append("number")
        if evidence_numbers and len(evidence_numbers) >= 2:
            covered.append("comparison")
        if _TAXONOMY_RE.search(evidence_text):
            covered.append("taxonomy")
        if _RECOMMENDATION_RE.search(evidence_text):
            covered.append("recommendation")
        if _LIMITATION_RE.search(evidence_text):
            covered.extend(["limitation", "safety_boundary"])
        if evidence_text.strip():
            covered.extend(["method", "result"])
        return list(dict.fromkeys(covered))

    @staticmethod
    def _targeted_queries(
        *,
        missing_papers: list[str],
        missing_claim_types: list[str],
        requirement: EvidenceRequirement,
    ) -> list[str]:
        queries: list[str] = []
        claim_words = " ".join(_claim_type_query_terms(missing_claim_types or requirement.required_claim_types))
        for paper_id in missing_papers:
            queries.append(f"{paper_id} {claim_words} evidence".strip())
        if not queries and missing_claim_types:
            queries.append(f"{claim_words} evidence".strip())
        return queries


def _claim_type_query_terms(claim_types: list[str]) -> list[str]:
    mapping = {
        "number": "numbers",
        "comparison": "comparison",
        "taxonomy": "taxonomy classification labels",
        "method": "method",
        "result": "result",
        "recommendation": "recommendations defenses",
        "limitation": "limitations",
        "safety_boundary": "claim boundaries limitations",
    }
    terms: list[str] = []
    for claim_type in claim_types:
        terms.extend(mapping.get(claim_type, claim_type).split())
    return list(dict.fromkeys(terms))


def _ordered_unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(value.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
```

- [ ] **Step 4: Run coverage tests**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_coverage_service.py -q
```

Expected: `3 passed`.

---

### Task 4: Wire Coverage Gate Into Bounded Orchestrator

**Files:**
- Modify: `apps/api/app/schemas/agent_trace.py`
- Modify: `apps/api/app/services/research_orchestrator.py`
- Modify: `apps/api/tests/test_research_orchestrator.py`

- [ ] **Step 1: Add orchestrator tests for coverage-driven retry**

Append to `apps/api/tests/test_research_orchestrator.py`:

```python
from app.schemas.reliability import EvidenceCoverageReport, EvidenceRequirement, QuestionIntent


class FakeCoverageEvaluator:
    def __init__(self, *reports: EvidenceCoverageReport) -> None:
        self.reports = list(reports)
        self.calls: list[dict[str, Any]] = []

    def evaluate(self, **kwargs: Any) -> EvidenceCoverageReport:
        self.calls.append(kwargs)
        if self.reports:
            return self.reports.pop(0)
        return EvidenceCoverageReport(
            requirement_id="er-test",
            status="strong",
            covered_paper_ids=["paper-1"],
            covered_claim_types=["result"],
        )


def _requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="er-test",
        intent=QuestionIntent(intent_type="numeric_grounding", confidence=0.9),
        required_claim_types=["number"],
        must_verify_numeric_claims=True,
    )


def test_coverage_gate_overrides_premature_sufficient_stop_with_targeted_retry() -> None:
    retrieval = FakeRetrieval({
        INITIAL_QUERY: [1],
        "numbers result evidence": [2],
    })
    planner = FakePlanner('{"stop_reason":"sufficient","confidence_band":"high"}')
    coverage = FakeCoverageEvaluator(
        EvidenceCoverageReport(
            requirement_id="er-test",
            status="partial",
            covered_paper_ids=["paper-1"],
            missing_claim_types=["number"],
            targeted_queries=["numbers result evidence"],
            limits=["Missing required claim-type coverage."],
        ),
        EvidenceCoverageReport(
            requirement_id="er-test",
            status="strong",
            covered_paper_ids=["paper-1"],
            covered_claim_types=["number"],
        ),
    )

    result = _run(
        ResearchOrchestrator(
            retrieval=retrieval,
            planner=planner,
            coverage_evaluator=coverage,
        ),
        _request(question="Which numbers support the result?").model_copy(
            update={"evidence_requirement": _requirement()}
        ),
    )

    assert [call["query"] for call in retrieval.calls] == [INITIAL_QUERY, "numbers result evidence"]
    assert result.coverage_report is not None
    assert result.coverage_report.status == "strong"
    assert any(action.state == "coverage_check" for action in result.agent_trace.actions)
```

- [ ] **Step 2: Run the new orchestrator test and verify it fails**

Run:

```powershell
python -m pytest apps/api/tests/test_research_orchestrator.py::test_coverage_gate_overrides_premature_sufficient_stop_with_targeted_retry -q
```

Expected: `ResearchOrchestrator.__init__` or request field failure.

- [ ] **Step 3: Extend trace and orchestrator data models**

In `apps/api/app/schemas/agent_trace.py`, add `"coverage_check"` to `AgentState`.

In `apps/api/app/services/research_orchestrator.py`:

- Import `EvidenceCoverageReport`, `EvidenceRequirement`, and `EvidenceCoverageService`.
- Add `evidence_requirement: EvidenceRequirement | None = None` to `OrchestratorRequest`.
- Add `coverage_report: EvidenceCoverageReport | None = None` to `OrchestratorResult`.
- Add constructor parameter `coverage_evaluator: Any | None = None`; default to `EvidenceCoverageService()`.
- After each retrieval pass and before accepting planner `sufficient`, evaluate coverage if `request.evidence_requirement` exists.
- If coverage is not `strong` and `coverage_report.targeted_queries` is non-empty, run one bounded retry with those queries before final answer.
- Add an `AgentTraceAction(state="coverage_check", ...)` with sanitized missing evidence in `missing_evidence` and `note=f"coverage status: {coverage_report.status}"`.

The implementation should keep the existing three-pass budget and `MAX_QUERIES_PER_PASS` clamp. Coverage-targeted queries must go through the same `_validated_planner_queries` safety path or an equivalent sanitizer that rejects unsafe trace text.

- [ ] **Step 4: Run focused orchestrator tests**

Run:

```powershell
python -m pytest apps/api/tests/test_research_orchestrator.py -q
```

Expected: all orchestrator tests pass.

---

### Task 5: Add Conservative Answer Claim Verifier

**Files:**
- Create: `apps/api/app/services/answer_claim_verifier.py`
- Create: `apps/api/tests/test_answer_claim_verifier.py`

- [ ] **Step 1: Write claim verifier tests**

Create `apps/api/tests/test_answer_claim_verifier.py`:

```python
from app.schemas.evidence import EvidenceCitation, EvidencePacket, EvidenceUnit
from app.schemas.reliability import EvidenceCoverageReport, EvidenceRequirement, QuestionIntent
from app.services.answer_claim_verifier import AnswerClaimVerifier


def _packet() -> EvidencePacket:
    unit = EvidenceUnit(
        evidence_id="ev-p1-1",
        paper_id="p1",
        page_number=1,
        source="hybrid_page",
        score=0.9,
        caption="The evaluation reports 80% success and recommends runtime policy enforcement.",
        validation_state="validated",
    )
    return EvidencePacket(
        packet_id="ep-test",
        query="test",
        paper_scope=["p1"],
        units=[unit],
        citations=[EvidenceCitation(evidence_id=unit.evidence_id, paper_id="p1", page_number=1, label="p1 p.1")],
    )


def _requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="er-test",
        intent=QuestionIntent(intent_type="numeric_grounding", confidence=0.9),
        required_claim_types=["number", "recommendation"],
        must_verify_numeric_claims=True,
    )


def test_claim_verifier_supports_claim_with_matching_number_and_text() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The paper reports 80% success and recommends runtime policy enforcement.",
        requirement=_requirement(),
        coverage=EvidenceCoverageReport(requirement_id="er-test", status="strong"),
        packet=_packet(),
    )

    assert report.status == "strong"
    assert report.unsupported_claim_count == 0
    assert report.claims[0].support_status == "supported"


def test_claim_verifier_flags_unseen_number() -> None:
    report = AnswerClaimVerifier().verify(
        answer="The paper reports 94% success.",
        requirement=_requirement(),
        coverage=EvidenceCoverageReport(requirement_id="er-test", status="strong"),
        packet=_packet(),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert report.claims[0].support_status == "unsupported"


def test_claim_verifier_flags_broad_product_overclaim() -> None:
    report = AnswerClaimVerifier().verify(
        answer="PaperMemory detects all malicious skills and guarantees safe execution.",
        requirement=_requirement(),
        coverage=EvidenceCoverageReport(requirement_id="er-test", status="partial"),
        packet=_packet(),
    )

    assert report.status == "partial"
    assert report.unsupported_claim_count == 1
    assert "universal" in report.claims[0].reason.lower()
```

- [ ] **Step 2: Run verifier tests and verify they fail**

Run:

```powershell
python -m pytest apps/api/tests/test_answer_claim_verifier.py -q
```

Expected: import failure for `AnswerClaimVerifier`.

- [ ] **Step 3: Implement verifier**

Create `apps/api/app/services/answer_claim_verifier.py` with deterministic checks:

```python
from __future__ import annotations

import re

from app.schemas.evidence import EvidencePacket
from app.schemas.reliability import (
    AnswerReliabilityReport,
    ClaimSupport,
    EvidenceCoverageReport,
    EvidenceRequirement,
)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+-\s+")
_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*%?|\b\d+\s*/\s*\d+\b")
_UNIVERSAL_OVERCLAIM_RE = re.compile(
    r"\b(all|always|guarantee[sd]?|detects? all|prevents? all|safe execution|malware detection)\b",
    re.I,
)


class AnswerClaimVerifier:
    """Conservative verifier that marks unsupported claims instead of repairing prose."""

    def verify(
        self,
        *,
        answer: str,
        requirement: EvidenceRequirement,
        coverage: EvidenceCoverageReport,
        packet: EvidencePacket | None,
    ) -> AnswerReliabilityReport:
        evidence_text = self._evidence_text(packet)
        evidence_ids = [unit.evidence_id for unit in packet.units] if packet is not None else []
        claims: list[ClaimSupport] = []
        for sentence in self._claim_sentences(answer):
            support = self._support_for(sentence, evidence_text, evidence_ids)
            claims.append(support)

        unsupported_count = sum(1 for claim in claims if claim.support_status == "unsupported")
        limits = list(coverage.limits)
        if unsupported_count:
            limits.append("One or more answer claims are not supported by accepted evidence.")
        if coverage.status == "insufficient":
            status = "insufficient"
        elif unsupported_count or coverage.status == "partial":
            status = "partial"
        else:
            status = "strong"
        return AnswerReliabilityReport(
            status=status,
            requirement=requirement,
            coverage=coverage,
            claims=claims,
            unsupported_claim_count=unsupported_count,
            limits=limits,
        )

    @staticmethod
    def _evidence_text(packet: EvidencePacket | None) -> str:
        if packet is None:
            return ""
        return "\n".join(" ".join(filter(None, [unit.title, unit.caption])) for unit in packet.units).lower()

    @staticmethod
    def _claim_sentences(answer: str) -> list[str]:
        raw_sentences = [part.strip(" -\n\t") for part in _SENTENCE_RE.split(answer) if part.strip()]
        return [sentence for sentence in raw_sentences if len(sentence) >= 20][:12]

    def _support_for(self, sentence: str, evidence_text: str, evidence_ids: list[str]) -> ClaimSupport:
        lowered = sentence.lower()
        if _UNIVERSAL_OVERCLAIM_RE.search(sentence):
            return ClaimSupport(
                claim_text=sentence,
                support_status="unsupported",
                evidence_ids=[],
                reason="Universal or product-capability claim is not supported by accepted paper evidence.",
            )
        numbers = _NUMBER_RE.findall(sentence)
        missing_numbers = [number for number in numbers if number.lower() not in evidence_text]
        if missing_numbers:
            return ClaimSupport(
                claim_text=sentence,
                support_status="unsupported",
                evidence_ids=[],
                reason=f"Numeric claim not found in accepted evidence: {', '.join(missing_numbers)}.",
            )
        tokens = [token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", lowered) if token not in {"paper", "papers", "evidence", "answer"}]
        matched = sum(1 for token in tokens if token in evidence_text)
        if tokens and matched >= max(1, min(3, len(tokens) // 3)):
            return ClaimSupport(
                claim_text=sentence,
                support_status="supported",
                evidence_ids=evidence_ids[:4],
                reason="Claim terms are present in accepted evidence.",
            )
        return ClaimSupport(
            claim_text=sentence,
            support_status="partially_supported" if evidence_text else "unsupported",
            evidence_ids=evidence_ids[:2],
            reason="Claim is only partially grounded in accepted evidence.",
        )
```

- [ ] **Step 4: Run verifier tests**

Run:

```powershell
python -m pytest apps/api/tests/test_answer_claim_verifier.py -q
```

Expected: `3 passed`.

---

### Task 6: Integrate Reliability Report Into `/chat`

**Files:**
- Modify: `apps/api/app/schemas/chat.py`
- Modify: `apps/api/app/services/chat_service.py`
- Modify: `apps/api/app/services/context_builder.py`
- Modify: `apps/api/app/routers/chat.py`
- Create: `apps/api/tests/test_chat_reliability_layer.py`
- Update: existing chat/streaming tests if strict response shape assertions fail.

- [ ] **Step 1: Write integration tests for non-streaming `/chat` service**

Create `apps/api/tests/test_chat_reliability_layer.py`:

```python
import asyncio
from typing import Any

from app.schemas.agent_trace import AgentTrace, AgentTraceAction
from app.schemas.chat import ChatRequest
from app.schemas.evidence import EvidenceCitation, EvidencePacket, EvidenceRankTrace, EvidenceUnit
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.hybrid_retrieval_service import HybridRetrievalResult
from app.services.model_gateway import BuiltUserContent, GenerationResponse, ModelGateway
from app.services.research_orchestrator import OrchestratorResult


class Gateway(ModelGateway):
    async def generate(self, messages: Any, **kwargs: Any) -> GenerationResponse:
        return GenerationResponse(
            text="The accepted evidence reports 80% success and recommends runtime policy enforcement.",
            model="stub",
        )

    async def generate_stream(self, messages: Any, **kwargs: Any):
        yield "The accepted evidence reports 80% success."

    def build_user_content(self, text: str, image_paths: list[str], **kwargs: Any) -> BuiltUserContent:
        return BuiltUserContent(content=text, included_image_count=0)


class OrchestratorFactory:
    def __init__(self, result: OrchestratorResult) -> None:
        self.result = result
        self.requests: list[Any] = []

    def __call__(self, **kwargs: Any):
        factory = self

        class Runner:
            async def run(self, request: Any) -> OrchestratorResult:
                factory.requests.append(request)
                return factory.result

        return Runner()


def _result() -> OrchestratorResult:
    evidence = [PageEvidence(paper_id="p1", page_number=1, score=0.8, caption="The evaluation reports 80% success and recommends runtime policy enforcement.")]
    unit = EvidenceUnit(
        evidence_id="ev-p1-1",
        paper_id="p1",
        page_number=1,
        source="hybrid_page",
        score=0.8,
        caption=evidence[0].caption,
        rank_trace=[EvidenceRankTrace(retriever="bm25", source="text_page", rank=1, score=12.0)],
        validation_state="validated",
    )
    packet = EvidencePacket(
        packet_id="ep-test",
        query="numbers evidence",
        paper_scope=["p1"],
        units=[unit],
        citations=[EvidenceCitation(evidence_id=unit.evidence_id, paper_id="p1", page_number=1, label="p1 p.1")],
    )
    trace = AgentTrace(
        trace_id="trace-test",
        actions=[AgentTraceAction(state="answer", pass_index=1, evidence_ids=[unit.evidence_id], stop_reason="sufficient")],
        final_stop_reason="sufficient",
    )
    return OrchestratorResult(evidence=evidence, evidence_packet=packet, agent_trace=trace, limits=[], coverage_report=None)


def test_chat_response_includes_reliability_report_when_enabled() -> None:
    service = ChatService(
        visrag=object(),
        vector_store=object(),
        model_gateway=Gateway(),
        research_orchestrator_factory=OrchestratorFactory(_result()),
        hybrid_retrieval=object(),
    )

    response = asyncio.run(
        service.answer(
            ChatRequest(
                question="Which numbers support the result?",
                paper_ids=["p1"],
                enable_reliability_layer=True,
            )
        )
    )

    assert response.reliability_report is not None
    assert response.reliability_report.status == "strong"
    assert response.reliability_report.requirement.intent.intent_type == "numeric_grounding"
```

- [ ] **Step 2: Run integration test and verify it fails**

Run:

```powershell
python -m pytest apps/api/tests/test_chat_reliability_layer.py -q
```

Expected: `ChatRequest` missing `enable_reliability_layer` or `ChatResponse` missing `reliability_report`.

- [ ] **Step 3: Extend chat schemas**

In `apps/api/app/schemas/chat.py`:

- Import `AnswerReliabilityReport`.
- Add `enable_reliability_layer: bool = True` to `ChatRequest`.
- Add `reliability_report: AnswerReliabilityReport | None = None` to `ChatResponse`.

- [ ] **Step 4: Wire services in `ChatService`**

In `apps/api/app/services/chat_service.py`:

- Instantiate `EvidenceRequirementService`, `EvidenceCoverageService`, and `AnswerClaimVerifier` in `__init__`, with optional dependency injection for tests.
- In `answer()`, before retrieval, call `requirement_service.plan(...)` when `request.enable_reliability_layer` is true.
- Pass the requirement into `OrchestratorRequest`.
- After retrieval and generation, evaluate coverage if the orchestrator did not already return it.
- Run `AnswerClaimVerifier.verify(...)` and attach the report to `ChatResponse`.
- Merge report limits into existing response limits with `_merge_limits`.
- Keep existing behavior when `enable_reliability_layer=False`.

- [ ] **Step 5: Update generation prompt contract**

In `apps/api/app/services/context_builder.py`, extend `build_evidence_packet_prompt(...)` with a short generic block when an evidence requirement is supplied:

```text
Evidence reliability contract:
- Required claim types: ...
- Inference policy: ...
- If accepted evidence does not support a claim, label it as missing or omit it.
- Do not upgrade a controlled evidence answer into a broad product or safety guarantee.
```

Keep this block generic. Do not mention the skill-security papers or their numbers.

- [ ] **Step 6: Include reliability report in streaming done frames**

In `apps/api/app/services/chat_service.py::answer_stream`, compute the same reliability report after `clean_answer` and include it in the final yielded dict as `reliability_report`. Do not include reliability report in the early evidence frame because claim verification requires the final answer.

In `apps/api/app/routers/chat.py`, no custom serialization should be needed if the final chunk already includes the Pydantic model and `_json_default` handles it.

- [ ] **Step 7: Run chat reliability tests and focused regression tests**

Run:

```powershell
python -m pytest apps/api/tests/test_chat_reliability_layer.py apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_chat_prompt.py -q
```

Expected: all selected tests pass.

---

### Task 7: Add Frontend Reliability Display Without UI Churn

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/use-chat-session.ts`
- Modify one display component: `apps/web/components/evidence-panel.tsx` or `apps/web/components/chat-panel.tsx`

- [ ] **Step 1: Add TypeScript types**

In `apps/web/lib/types.ts`, add optional reliability types mirroring the API:

```ts
export type AnswerQualityStatus = "strong" | "partial" | "insufficient";

export interface ApiAnswerReliabilityReport {
  status: AnswerQualityStatus;
  unsupported_claim_count: number;
  limits: string[];
  coverage: {
    status: AnswerQualityStatus;
    covered_paper_ids: string[];
    missing_paper_ids: string[];
    covered_claim_types: string[];
    missing_claim_types: string[];
    matched_numbers: string[];
    missing_numbers: string[];
    targeted_queries: string[];
    limits: string[];
  };
}
```

Add `reliability_report?: ApiAnswerReliabilityReport | null` to chat response and message state types.

- [ ] **Step 2: Preserve reliability report through API client**

In `apps/web/lib/api.ts`, ensure non-streaming and streaming final response objects retain `reliability_report`. Existing object spreading may already preserve it; if not, explicitly include it next to `evidence_packet`, `agent_trace`, and `stats`.

- [ ] **Step 3: Store report in chat state**

In `apps/web/lib/use-chat-session.ts`, attach `response.reliability_report ?? null` and `done.reliability_report ?? null` to the assistant message.

- [ ] **Step 4: Display a compact badge**

In the chosen component, render a small status label only when a reliability report exists:

```tsx
const reliabilityLabel = message.reliability_report?.status;
```

Use concise labels:

- `strong` -> `Evidence strong`
- `partial` -> `Evidence partial`
- `insufficient` -> `Evidence insufficient`

Do not add a large explanatory panel. The UI should remain focused on chat and evidence.

- [ ] **Step 5: Run frontend type checks**

Run:

```powershell
npm --workspace apps/web run lint
```

If the repo does not define a lint script for the web workspace, run the existing project check command from `package.json` and record the exact command/output in `.planning/2026-06-27-paper-memory-evidence-reliability-layer/progress.md`.

---

### Task 8: Add Generic Evaluation Harness And Report Artifact

**Files:**
- Create: `eval/evidence_reliability_general_testset.json`
- Create: `reports/final/results/evidence_reliability_layer.md`
- Modify or create focused tests under `apps/api/tests/`

- [ ] **Step 1: Create generic test set**

Create `eval/evidence_reliability_general_testset.json` with domain-neutral cases:

```json
{
  "name": "evidence_reliability_general_testset",
  "purpose": "Generic reliability checks for PaperMemory evidence planning, coverage, claim verification, and answer quality status.",
  "cases": [
    {
      "id": "ER1",
      "capability": "numeric grounding",
      "question": "Which numbers in the selected papers support the result?",
      "expected_intent": "numeric_grounding",
      "expected_claim_types": ["number", "comparison"]
    },
    {
      "id": "ER2",
      "capability": "cross-document coverage",
      "question": "Compare the main findings across the selected papers.",
      "expected_intent": "cross_document_comparison",
      "expected_multi_paper_coverage": true
    },
    {
      "id": "ER3",
      "capability": "taxonomy classification",
      "question": "Classify the risk and cite which source supports each label.",
      "expected_intent": "taxonomy_classification",
      "expected_claim_types": ["taxonomy"]
    },
    {
      "id": "ER4",
      "capability": "claim boundary",
      "question": "What can the report claim, and what should it not overclaim?",
      "expected_intent": "claim_boundary",
      "expected_claim_types": ["recommendation", "safety_boundary", "limitation"]
    }
  ]
}
```

- [ ] **Step 2: Add a lightweight eval test**

Create `apps/api/tests/test_evidence_reliability_eval.py`:

```python
import json
from pathlib import Path

from app.services.evidence_requirement_service import EvidenceRequirementService


def test_general_reliability_eval_cases_map_to_expected_intents() -> None:
    path = Path(__file__).parents[3] / "eval" / "evidence_reliability_general_testset.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    service = EvidenceRequirementService()

    for case in data["cases"]:
        requirement = service.plan(question=case["question"], paper_ids=["p1", "p2"])
        assert requirement.intent.intent_type == case["expected_intent"]
        for claim_type in case.get("expected_claim_types", []):
            assert claim_type in requirement.required_claim_types
        if case.get("expected_multi_paper_coverage"):
            assert requirement.requires_multi_paper_coverage is True
```

- [ ] **Step 3: Create report-facing artifact**

Create `reports/final/results/evidence_reliability_layer.md`:

```markdown
# Evidence Reliability Layer

The Evidence Reliability Layer upgrades PaperMemory from a retrieval-and-answer pipeline into a bounded evidence agent. It does not hardcode any source paper or answer. It plans generic evidence requirements, checks accepted evidence coverage, verifies final answer claims, and returns a calibrated answer-quality status.

## Report Claim

Supported claim: PaperMemory can expose whether a generated answer is strongly grounded, partially grounded, or insufficiently grounded in accepted evidence.

Unsupported claim: this layer does not prove exhaustive literature-review coverage, universal malicious-skill detection, or autonomous safe execution.

## Mechanism

- Question intent planner: maps questions to generic evidence requirements.
- Coverage gate: checks paper coverage, claim-type coverage, and numeric evidence.
- Claim verifier: flags unsupported numbers and broad product overclaims.
- Public reliability report: exposes `strong`, `partial`, or `insufficient` status with limits.

## Demo Use

Use the reliability badge and report object to explain why a strong answer can be promoted into the report, why a partial answer needs human review, and why an insufficient answer should be treated as a visible failure boundary instead of hidden model uncertainty.
```

- [ ] **Step 4: Run reliability eval tests**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_reliability_eval.py -q
```

Expected: `1 passed`.

---

### Task 9: Final Verification And Handoff

**Files:**
- Modify: `.planning/2026-06-27-paper-memory-evidence-reliability-layer/progress.md`
- Modify: `.planning/2026-06-27-paper-memory-evidence-reliability-layer/findings.md`
- Modify: `.planning/2026-06-27-paper-memory-evidence-reliability-layer/task_plan.md`

- [ ] **Step 1: Run focused backend reliability suite**

Run:

```powershell
python -m pytest apps/api/tests/test_evidence_requirement_service.py apps/api/tests/test_evidence_coverage_service.py apps/api/tests/test_answer_claim_verifier.py apps/api/tests/test_chat_reliability_layer.py apps/api/tests/test_evidence_reliability_eval.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run safety and agentic regression suite**

Run:

```powershell
python -m pytest apps/api/tests/test_research_orchestrator.py apps/api/tests/test_prompt_injection_pdf.py apps/api/tests/test_retrieval_robustness.py apps/api/tests/test_chat_streaming.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run serialization and formatting checks**

Run:

```powershell
python -m json.tool eval\evidence_reliability_general_testset.json > $null
git diff --check -- apps/api/app apps/api/tests apps/web eval reports docs .planning
```

Expected: JSON validates and `git diff --check` exits `0`.

- [ ] **Step 4: Update durable planning files**

Record:

- Tests run and exact outcomes.
- Whether frontend type/lint checks ran or were unavailable.
- Any change to final report/demo wording.
- Known limitations: deterministic verifier is conservative, page-level retrieval remains the retrieval base, and OCR/table extraction remains future work.

- [ ] **Step 5: Prepare subagent-driven execution**

When executing this plan, use disjoint subagent tasks:

- Worker 1: schemas + requirement planner.
- Worker 2: coverage service + orchestrator gate.
- Worker 3: claim verifier + chat integration.
- Worker 4: frontend badge + report artifact.
- Reviewer 1: spec compliance.
- Reviewer 2: code quality and robustness boundaries.

Do not run all workers in parallel if they touch the same files. The efficient order is Task 1-2 first, Task 3 next, Task 4 after coverage exists, Task 5-6 after orchestrator integration, then Task 7-9.
