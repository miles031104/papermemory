from __future__ import annotations

import inspect
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.schemas.agent_trace import (
    AgentStopReason,
    AgentTrace,
    AgentTraceAction,
    PlannerDecision,
    sanitize_trace_text,
)
from app.schemas.chat import ChatMessage
from app.schemas.evidence import (
    EvidenceCitation,
    EvidencePacket,
    EvidenceUnit,
    deterministic_packet_id,
)
from app.schemas.reliability import EvidenceCoverageReport, EvidenceRequirement
from app.schemas.retrieval import PageEvidence
from app.services.context_builder import build_conversational_query, build_evidence_analysis_prompt
from app.services.evidence_coverage_service import EvidenceCoverageService
from app.services.evidence_validator import validate_evidence_packet

MAX_RETRIEVAL_PASSES = 3
MAX_QUERIES_PER_PASS = 4
MAX_FINAL_EVIDENCE_UNITS = 8
RETRIEVAL_PASS_FAILED_NOTE = "retrieval pass failed; bounded partial result returned"
RETRIEVAL_PASS_FAILED_LIMIT = (
    "Retrieval pass failed; returning bounded partial evidence instead of continuing unbounded."
)
_UNSAFE_PLANNER_HINT_RE = re.compile(
    r"(?i)\b(change\s+citations?|execute\s+(?:tools?|commands?)|"
    r"reveal\s+(?:api[_ -]?keys?|secrets?|credentials?|tokens?))\b"
)

PlannerCallable = Callable[["str", "OrchestratorRequest"], Awaitable[str] | str | Any]


@dataclass(frozen=True)
class OrchestratorRequest:
    question: str
    paper_ids: list[str]
    top_k: int
    score_threshold: float | None
    max_per_paper: int | None
    messages: list[ChatMessage]
    model: str | None
    base_url: str | None
    api_key: str | None
    evidence_requirement: EvidenceRequirement | None = None


@dataclass(frozen=True)
class OrchestratorResult:
    evidence: list[PageEvidence]
    evidence_packet: EvidencePacket
    agent_trace: AgentTrace
    limits: list[str]
    coverage_report: EvidenceCoverageReport | None = None


class ResearchOrchestrator:
    """Bounded three-pass evidence retrieval state machine."""

    def __init__(
        self,
        *,
        retrieval: Any,
        planner: PlannerCallable,
        query_builder: Callable[[str, list[ChatMessage]], str] = build_conversational_query,
        coverage_evaluator: Any | None = None,
    ) -> None:
        self.retrieval = retrieval
        self.planner = planner
        self.query_builder = query_builder
        self.coverage_evaluator = coverage_evaluator or EvidenceCoverageService()

    async def run(self, request: OrchestratorRequest) -> OrchestratorResult:
        actions: list[AgentTraceAction] = []
        limits = [
            f"max_passes={MAX_RETRIEVAL_PASSES}",
            f"max_queries_per_pass={MAX_QUERIES_PER_PASS}",
            f"max_final_evidence_units={MAX_FINAL_EVIDENCE_UNITS}",
        ]
        merged_units: list[EvidenceUnit] = []
        merged_evidence: list[PageEvidence] = []
        seen_ids: set[str] = set()
        seen_page_sources: set[tuple[str, int, str]] = set()
        coverage_report: EvidenceCoverageReport | None = None
        targeted_retry_used = False
        next_retrieval_pass_index = 2

        initial_query = self.query_builder(request.question, request.messages)
        actions.append(
            AgentTraceAction(
                state="query_rewrite",
                pass_index=0,
                query=initial_query,
                note="conversation-aware query prepared",
            )
        )

        first_delta = await self._run_retrieval_pass(
            request=request,
            queries=[initial_query],
            pass_index=1,
            state="first_retrieval",
            actions=actions,
            merged_units=merged_units,
            merged_evidence=merged_evidence,
            seen_ids=seen_ids,
            seen_page_sources=seen_page_sources,
            limits=limits,
        )
        (
            coverage_report,
            targeted_retry_used,
            retry_consumed_pass,
        ) = await self._evaluate_coverage_after_retrieval(
            request=request,
            merged_units=merged_units,
            merged_evidence=merged_evidence,
            actions=actions,
            seen_ids=seen_ids,
            seen_page_sources=seen_page_sources,
            limits=limits,
            pass_index=1,
            targeted_retry_used=targeted_retry_used,
            retry_pass_index=2,
            retry_state="second_retrieval",
        )
        if retry_consumed_pass:
            next_retrieval_pass_index = 3
        if first_delta == 0 and not merged_units:
            actions.append(
                AgentTraceAction(
                    state="sufficiency_check",
                    pass_index=1,
                    evidence_ids=[],
                    evidence_delta_count=0,
                    stop_reason="insufficient_evidence",
                    note="first retrieval returned no accepted evidence",
                )
            )

        decision = await self._plan(
            request=request,
            units=merged_units,
            actions=actions,
            pass_index=1,
        )
        stop_reason = self._decision_stop_reason(decision, bool(merged_units))
        if stop_reason is not None:
            return self._build_result(
                request=request,
                merged_units=merged_units,
                merged_evidence=merged_evidence,
                actions=actions,
                final_stop_reason=stop_reason,
                limits=limits,
                coverage_report=coverage_report,
            )

        planner_retrieval_pass_index = next_retrieval_pass_index
        planner_queries = self._validated_planner_queries(
            decision,
            actions,
            pass_index=min(planner_retrieval_pass_index, MAX_RETRIEVAL_PASSES),
        )
        if not planner_queries:
            final_stop: AgentStopReason = "sufficient" if merged_units else "insufficient_evidence"
            return self._build_result(
                request=request,
                merged_units=merged_units,
                merged_evidence=merged_evidence,
                actions=actions,
                final_stop_reason=final_stop,
                limits=limits,
                coverage_report=coverage_report,
            )
        if planner_retrieval_pass_index > MAX_RETRIEVAL_PASSES:
            return self._build_result(
                request=request,
                merged_units=merged_units,
                merged_evidence=merged_evidence,
                actions=actions,
                final_stop_reason="budget_exhausted",
                limits=limits,
                coverage_report=coverage_report,
            )

        planner_delta = await self._run_retrieval_pass(
            request=request,
            queries=planner_queries,
            pass_index=planner_retrieval_pass_index,
            state=self._retrieval_state_for_pass(planner_retrieval_pass_index),
            actions=actions,
            merged_units=merged_units,
            merged_evidence=merged_evidence,
            seen_ids=seen_ids,
            seen_page_sources=seen_page_sources,
            limits=limits,
        )
        next_retrieval_pass_index = planner_retrieval_pass_index + 1
        retry_pass_index = (
            next_retrieval_pass_index
            if next_retrieval_pass_index <= MAX_RETRIEVAL_PASSES
            else None
        )
        (
            coverage_report,
            targeted_retry_used,
            retry_consumed_pass,
        ) = await self._evaluate_coverage_after_retrieval(
            request=request,
            merged_units=merged_units,
            merged_evidence=merged_evidence,
            actions=actions,
            seen_ids=seen_ids,
            seen_page_sources=seen_page_sources,
            limits=limits,
            pass_index=planner_retrieval_pass_index,
            targeted_retry_used=targeted_retry_used,
            retry_pass_index=retry_pass_index,
            retry_state=(
                self._retrieval_state_for_pass(retry_pass_index)
                if retry_pass_index is not None
                else None
            ),
        )
        if retry_consumed_pass:
            next_retrieval_pass_index += 1
        actions.append(
            AgentTraceAction(
                state="sufficiency_check",
                pass_index=planner_retrieval_pass_index,
                evidence_ids=[unit.evidence_id for unit in merged_units],
                evidence_delta_count=planner_delta,
                stop_reason="no_new_evidence" if planner_delta == 0 else None,
                note="retrieval pass evidence delta checked",
            )
        )
        if planner_delta == 0:
            final_stop = (
                "sufficient"
                if coverage_report is not None and coverage_report.status == "strong"
                else "no_new_evidence"
            )
            return self._build_result(
                request=request,
                merged_units=merged_units,
                merged_evidence=merged_evidence,
                actions=actions,
                final_stop_reason=final_stop,
                limits=limits,
                coverage_report=coverage_report,
            )

        decision = await self._plan(
            request=request,
            units=merged_units,
            actions=actions,
            pass_index=planner_retrieval_pass_index,
        )
        stop_reason = self._decision_stop_reason(decision, bool(merged_units))
        if stop_reason is not None:
            return self._build_result(
                request=request,
                merged_units=merged_units,
                merged_evidence=merged_evidence,
                actions=actions,
                final_stop_reason=stop_reason,
                limits=limits,
                coverage_report=coverage_report,
            )

        final_query_pass_index = next_retrieval_pass_index
        final_queries = self._validated_planner_queries(
            decision,
            actions,
            pass_index=min(final_query_pass_index, MAX_RETRIEVAL_PASSES),
        )
        if final_queries:
            if final_query_pass_index > MAX_RETRIEVAL_PASSES:
                return self._build_result(
                    request=request,
                    merged_units=merged_units,
                    merged_evidence=merged_evidence,
                    actions=actions,
                    final_stop_reason="budget_exhausted",
                    limits=limits,
                    coverage_report=coverage_report,
                )
            await self._run_retrieval_pass(
                request=request,
                queries=final_queries,
                pass_index=final_query_pass_index,
                state=self._retrieval_state_for_pass(final_query_pass_index),
                actions=actions,
                merged_units=merged_units,
                merged_evidence=merged_evidence,
                seen_ids=seen_ids,
                seen_page_sources=seen_page_sources,
                limits=limits,
            )
            (
                coverage_report,
                targeted_retry_used,
                retry_consumed_pass,
            ) = await self._evaluate_coverage_after_retrieval(
                request=request,
                merged_units=merged_units,
                merged_evidence=merged_evidence,
                actions=actions,
                seen_ids=seen_ids,
                seen_page_sources=seen_page_sources,
                limits=limits,
                pass_index=final_query_pass_index,
                targeted_retry_used=targeted_retry_used,
                retry_pass_index=None,
                retry_state=None,
            )
            final_stop: AgentStopReason = "budget_exhausted"
        else:
            final_stop = "sufficient" if merged_units else "insufficient_evidence"

        return self._build_result(
            request=request,
            merged_units=merged_units,
            merged_evidence=merged_evidence,
            actions=actions,
            final_stop_reason=final_stop,
            limits=limits,
            coverage_report=coverage_report,
        )

    async def _run_retrieval_pass(
        self,
        *,
        request: OrchestratorRequest,
        queries: list[str],
        pass_index: int,
        state: str,
        actions: list[AgentTraceAction],
        merged_units: list[EvidenceUnit],
        merged_evidence: list[PageEvidence],
        seen_ids: set[str],
        seen_page_sources: set[tuple[str, int, str]],
        limits: list[str],
    ) -> int:
        pass_delta = 0
        for query in queries[:MAX_QUERIES_PER_PASS]:
            try:
                result = await self.retrieval.search(
                    query=query,
                    paper_ids=request.paper_ids,
                    top_k=request.top_k,
                    score_threshold=request.score_threshold,
                    max_per_paper=request.max_per_paper,
                )
                new_units, new_evidence = self._new_units_from_result(
                    result=result,
                    seen_ids=seen_ids,
                    seen_page_sources=seen_page_sources,
                )
            except Exception:
                self._merge_limits(limits, [RETRIEVAL_PASS_FAILED_LIMIT])
                actions.append(
                    AgentTraceAction(
                        state=state,  # type: ignore[arg-type]
                        pass_index=pass_index,
                        query=query,
                        retrieval_mode="hybrid",
                        evidence_delta_count=0,
                        note=RETRIEVAL_PASS_FAILED_NOTE,
                    )
                )
                continue

            self._merge_limits(limits, list(getattr(result, "limits", [])))
            merged_units.extend(new_units)
            merged_evidence.extend(new_evidence)
            pass_delta += len(new_units)
            actions.append(
                AgentTraceAction(
                    state=state,  # type: ignore[arg-type]
                    pass_index=pass_index,
                    query=query,
                    retrieval_mode="hybrid",
                    evidence_ids=[unit.evidence_id for unit in merged_units],
                    new_evidence_ids=[unit.evidence_id for unit in new_units],
                    evidence_delta_count=len(new_units),
                )
            )
        return pass_delta

    async def _plan(
        self,
        *,
        request: OrchestratorRequest,
        units: list[EvidenceUnit],
        actions: list[AgentTraceAction],
        pass_index: int,
    ) -> PlannerDecision:
        packet = self._packet_from_units(
            query=request.question,
            paper_scope=request.paper_ids,
            units=units[:MAX_FINAL_EVIDENCE_UNITS],
            limits=[],
        )
        prompt = build_evidence_analysis_prompt(
            question=request.question,
            evidence_packet=packet,
            trace_actions=actions,
            pass_index=pass_index,
        )
        try:
            response = self.planner(prompt, request)
            if inspect.isawaitable(response):
                response = await response
            text = getattr(response, "text", response)
            decision = PlannerDecision.model_validate(self._load_json_object(str(text)))
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
            stop_reason: AgentStopReason = "sufficient" if units else "insufficient_evidence"
            actions.append(
                AgentTraceAction(
                    state="evidence_analysis",
                    pass_index=pass_index,
                    evidence_ids=[unit.evidence_id for unit in units],
                    stop_reason=stop_reason,
                    note="invalid planner JSON; safe stop selected",
                )
            )
            return PlannerDecision(stop_reason=stop_reason)

        actions.append(
            AgentTraceAction(
                state="evidence_analysis",
                pass_index=pass_index,
                retrieval_mode=decision.retrieval_mode,
                evidence_ids=[unit.evidence_id for unit in units],
                missing_evidence=self._safe_planner_items(decision.missing_evidence),
                stop_reason=decision.stop_reason,
                note=f"planner confidence: {decision.confidence_band}",
            )
        )
        return decision

    @staticmethod
    def _load_json_object(text: str) -> Any:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
            stripped = re.sub(r"\s*```$", "", stripped)
        return json.loads(stripped)

    @staticmethod
    def _decision_stop_reason(
        decision: PlannerDecision,
        has_evidence: bool,
    ) -> AgentStopReason | None:
        if decision.stop_reason == "sufficient" and not has_evidence:
            return "insufficient_evidence"
        if decision.stop_reason is not None:
            return decision.stop_reason
        return None

    def _validated_planner_queries(
        self,
        decision: PlannerDecision,
        actions: list[AgentTraceAction],
        pass_index: int,
    ) -> list[str]:
        if decision.retrieval_mode != "hybrid":
            actions.append(
                AgentTraceAction(
                    state="evidence_analysis",
                    pass_index=pass_index,
                    retrieval_mode=decision.retrieval_mode,
                    missing_evidence=self._safe_planner_items(decision.missing_evidence),
                    note="planner requested unsupported retrieval mode for this orchestrator",
                )
            )
            return []

        queries: list[str] = []
        for query in decision.next_queries[:MAX_QUERIES_PER_PASS]:
            sanitized = self._safe_planner_text(query)
            if not sanitized:
                continue
            queries.append(sanitized)
        return queries

    @staticmethod
    def _safe_planner_text(value: str | None) -> str | None:
        sanitized = sanitize_trace_text(value)
        if not sanitized or sanitized.startswith("[redacted"):
            return None
        if _UNSAFE_PLANNER_HINT_RE.search(sanitized):
            return None
        return sanitized

    @classmethod
    def _safe_planner_items(cls, values: list[str]) -> list[str]:
        safe_items: list[str] = []
        for value in values:
            safe = cls._safe_planner_text(value)
            if safe is not None:
                safe_items.append(safe)
        return safe_items

    def _new_units_from_result(
        self,
        *,
        result: Any,
        seen_ids: set[str],
        seen_page_sources: set[tuple[str, int, str]],
    ) -> tuple[list[EvidenceUnit], list[PageEvidence]]:
        packet = validate_evidence_packet(getattr(result, "evidence_packet"))
        evidence_by_page = {
            (item.paper_id, item.page_number): item
            for item in list(getattr(result, "evidence", []))
        }
        new_units: list[EvidenceUnit] = []
        new_evidence: list[PageEvidence] = []

        for unit in packet.units:
            page_source_key = (unit.paper_id, unit.page_number, unit.source)
            if unit.evidence_id in seen_ids or page_source_key in seen_page_sources:
                continue
            seen_ids.add(unit.evidence_id)
            seen_page_sources.add(page_source_key)
            new_units.append(unit)
            new_evidence.append(
                evidence_by_page.get((unit.paper_id, unit.page_number))
                or self._page_evidence_from_unit(unit)
            )
        return new_units, new_evidence

    @staticmethod
    def _page_evidence_from_unit(unit: EvidenceUnit) -> PageEvidence:
        return PageEvidence(
            paper_id=unit.paper_id,
            page_number=unit.page_number,
            score=float(unit.score or 0.0),
            image_url=unit.image_url,
            title=unit.title,
            caption=unit.caption,
            metadata=unit.metadata,
        )

    async def _evaluate_coverage_after_retrieval(
        self,
        *,
        request: OrchestratorRequest,
        merged_units: list[EvidenceUnit],
        merged_evidence: list[PageEvidence],
        actions: list[AgentTraceAction],
        seen_ids: set[str],
        seen_page_sources: set[tuple[str, int, str]],
        limits: list[str],
        pass_index: int,
        targeted_retry_used: bool,
        retry_pass_index: int | None,
        retry_state: str | None,
    ) -> tuple[EvidenceCoverageReport | None, bool, bool]:
        coverage_report = self._evaluate_coverage(
            request=request,
            merged_units=merged_units,
            actions=actions,
            pass_index=pass_index,
        )
        if (
            coverage_report is None
            or coverage_report.status == "strong"
            or not coverage_report.targeted_queries
            or targeted_retry_used
            or retry_pass_index is None
            or retry_state is None
        ):
            return coverage_report, targeted_retry_used, False

        targeted_retry_used = True
        await self._run_retrieval_pass(
            request=request,
            queries=coverage_report.targeted_queries,
            pass_index=retry_pass_index,
            state=retry_state,
            actions=actions,
            merged_units=merged_units,
            merged_evidence=merged_evidence,
            seen_ids=seen_ids,
            seen_page_sources=seen_page_sources,
            limits=limits,
        )
        coverage_report = self._evaluate_coverage(
            request=request,
            merged_units=merged_units,
            actions=actions,
            pass_index=retry_pass_index,
        )
        return coverage_report, targeted_retry_used, True

    @staticmethod
    def _retrieval_state_for_pass(pass_index: int) -> str:
        if pass_index == 1:
            return "first_retrieval"
        if pass_index == 2:
            return "second_retrieval"
        return "final_retrieval"

    def _evaluate_coverage(
        self,
        *,
        request: OrchestratorRequest,
        merged_units: list[EvidenceUnit],
        actions: list[AgentTraceAction],
        pass_index: int,
    ) -> EvidenceCoverageReport | None:
        if request.evidence_requirement is None:
            return None
        packet = self._packet_from_units(
            query=request.question,
            paper_scope=request.paper_ids,
            units=merged_units[:MAX_FINAL_EVIDENCE_UNITS],
            limits=[],
        )
        coverage_report = self.coverage_evaluator.evaluate(
            question=request.question,
            paper_ids=request.paper_ids,
            requirement=request.evidence_requirement,
            packet=packet,
        )
        actions.append(
            AgentTraceAction(
                state="coverage_check",
                pass_index=pass_index,
                evidence_ids=[unit.evidence_id for unit in merged_units[:MAX_FINAL_EVIDENCE_UNITS]],
                missing_evidence=self._coverage_missing_items(coverage_report),
                note=f"coverage status: {coverage_report.status}",
            )
        )
        return coverage_report

    @staticmethod
    def _coverage_missing_items(report: EvidenceCoverageReport) -> list[str]:
        items: list[str] = []
        if report.missing_paper_ids:
            items.append(f"missing papers: {', '.join(report.missing_paper_ids)}")
        if report.missing_claim_types:
            items.append(
                "missing claim types: "
                + ", ".join(claim_type.value for claim_type in report.missing_claim_types)
            )
        if report.missing_numbers:
            items.append(f"missing numbers: {', '.join(report.missing_numbers)}")
        return items

    def _build_result(
        self,
        *,
        request: OrchestratorRequest,
        merged_units: list[EvidenceUnit],
        merged_evidence: list[PageEvidence],
        actions: list[AgentTraceAction],
        final_stop_reason: AgentStopReason,
        limits: list[str],
        coverage_report: EvidenceCoverageReport | None = None,
    ) -> OrchestratorResult:
        final_units = list(merged_units)
        final_evidence = list(merged_evidence)
        if len(final_units) > MAX_FINAL_EVIDENCE_UNITS:
            final_units = final_units[:MAX_FINAL_EVIDENCE_UNITS]
            final_evidence = final_evidence[:MAX_FINAL_EVIDENCE_UNITS]
            self._merge_limits(limits, [f"final evidence units clamped to {MAX_FINAL_EVIDENCE_UNITS}"])

        actions.append(
            AgentTraceAction(
                state="answer",
                pass_index=min(MAX_RETRIEVAL_PASSES, max(1, actions[-1].pass_index if actions else 1)),
                evidence_ids=[unit.evidence_id for unit in final_units],
                stop_reason=final_stop_reason,
            )
        )
        trace = AgentTrace(
            trace_id=f"trace-{uuid.uuid4().hex[:12]}",
            actions=actions,
            final_stop_reason=final_stop_reason,
            limits=list(limits),
        )
        packet = validate_evidence_packet(
            self._packet_from_units(
                query=request.question,
                paper_scope=request.paper_ids,
                units=final_units,
                limits=limits,
            ),
            paper_scope=request.paper_ids,
        )
        return OrchestratorResult(
            evidence=final_evidence,
            evidence_packet=packet,
            agent_trace=trace,
            limits=list(limits),
            coverage_report=coverage_report,
        )

    @staticmethod
    def _packet_from_units(
        *,
        query: str,
        paper_scope: list[str],
        units: list[EvidenceUnit],
        limits: list[str],
    ) -> EvidencePacket:
        evidence_ids = [unit.evidence_id for unit in units]
        return EvidencePacket(
            packet_id=deterministic_packet_id(
                query=query,
                paper_scope=paper_scope,
                evidence_ids=evidence_ids,
            ),
            query=query,
            paper_scope=list(paper_scope),
            units=list(units),
            citations=[
                EvidenceCitation(
                    evidence_id=unit.evidence_id,
                    paper_id=unit.paper_id,
                    page_number=unit.page_number,
                    label=f"{unit.paper_id} p.{unit.page_number}",
                )
                for unit in units
            ],
            limits=list(limits),
        )

    @staticmethod
    def _merge_limits(target: list[str], new_limits: list[str]) -> None:
        seen = set(target)
        for limit in new_limits:
            if limit not in seen:
                target.append(limit)
                seen.add(limit)
