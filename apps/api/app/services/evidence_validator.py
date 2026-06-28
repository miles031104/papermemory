from __future__ import annotations

from typing import Any

from app.core.paths import StoragePaths
from app.schemas.evidence import EvidencePacket
from app.schemas.retrieval import redact_path_like_text


class EvidenceValidationError(ValueError):
    pass


def validate_evidence_packet(
    packet: EvidencePacket,
    *,
    paths: StoragePaths | None = None,
    paper_scope: list[str] | None = None,
    require_files: bool = False,
) -> EvidencePacket:
    units_by_id = {}
    for unit in packet.units:
        if unit.evidence_id in units_by_id:
            raise EvidenceValidationError(f"Duplicate evidence_id: {unit.evidence_id}")
        units_by_id[unit.evidence_id] = unit

        if unit.page_number < 1:
            raise EvidenceValidationError(
                f"Invalid page_number for {unit.evidence_id}: {unit.page_number}"
            )

    effective_scope = paper_scope if paper_scope is not None else packet.paper_scope
    if effective_scope is not None:
        allowed_papers = set(effective_scope)
        for unit in packet.units:
            if unit.paper_id not in allowed_papers:
                raise EvidenceValidationError(
                    f"Evidence {unit.evidence_id} paper_id {unit.paper_id!r} is outside paper scope"
                )

    for citation in packet.citations:
        unit = units_by_id.get(citation.evidence_id)
        if unit is None:
            raise EvidenceValidationError(
                f"Citation evidence_id {citation.evidence_id!r} is not present in packet units"
            )
        if (citation.paper_id, citation.page_number) != (unit.paper_id, unit.page_number):
            raise EvidenceValidationError(
                f"Citation {citation.evidence_id!r} does not match its evidence unit"
            )

    if paths is not None and require_files:
        _validate_files(packet, paths)

    _validate_public_serialization(packet)

    validated_units = [
        unit.model_copy(update={"validation_state": "validated"}) for unit in packet.units
    ]
    return packet.model_copy(update={"units": validated_units})


def _validate_files(packet: EvidencePacket, paths: StoragePaths) -> None:
    rendered_root = paths.rendered_pages_dir.resolve()
    for unit in packet.units:
        metadata_path = paths.paper_metadata_path(unit.paper_id)
        if not metadata_path.is_file():
            raise EvidenceValidationError(
                f"Missing paper metadata for {unit.paper_id!r}: {metadata_path}"
            )

        page_path = paths.page_image_path(unit.paper_id, unit.page_number).resolve()
        try:
            page_path.relative_to(rendered_root)
        except ValueError as exc:
            raise EvidenceValidationError(
                f"Resolved page image for {unit.evidence_id} is outside rendered_pages"
            ) from exc
        if not page_path.is_file():
            raise EvidenceValidationError(
                f"Missing page image for {unit.evidence_id}: {page_path}"
            )


def _validate_public_serialization(packet: EvidencePacket) -> None:
    for unit in packet.units:
        _assert_no_public_path(f"unit {unit.evidence_id} image_url", unit.image_url)
        _assert_no_public_path(f"unit {unit.evidence_id} title", unit.title)
        _assert_no_public_path(f"unit {unit.evidence_id} caption", unit.caption)
        _assert_no_public_path(f"unit {unit.evidence_id} metadata", unit.metadata)
        _assert_no_public_path(
            f"unit {unit.evidence_id} rank_trace",
            [trace.model_dump(mode="json") for trace in unit.rank_trace],
        )

    for citation in packet.citations:
        _assert_no_public_path(f"citation {citation.evidence_id} label", citation.label)

    _assert_no_public_path("evidence packet limits", packet.limits)


def _assert_no_public_path(field: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key) == "image_path":
                raise EvidenceValidationError(f"Public evidence packet exposes image_path in {field}")
            _assert_no_public_path(f"{field}.{key}", nested)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_public_path(f"{field}[{index}]", nested)
        return

    text = str(value)
    if redact_path_like_text(text) != text:
        raise EvidenceValidationError(f"Public evidence packet exposes a local path in {field}")
