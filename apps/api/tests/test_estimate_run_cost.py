from __future__ import annotations

import csv
import importlib.util
import sys
from decimal import Decimal
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "estimate_run_cost.py"
SPEC = importlib.util.spec_from_file_location("estimate_run_cost", SCRIPT_PATH)
assert SPEC is not None
estimate_run_cost = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = estimate_run_cost
SPEC.loader.exec_module(estimate_run_cost)


def test_net_savings_formula_includes_verification_api_and_license_costs() -> None:
    result = estimate_run_cost.net_savings_usd(
        manual_hours=Decimal("10"),
        papermemory_hours=Decimal("1"),
        verification_hours=Decimal("2"),
        fully_loaded_hourly_rate=Decimal("100"),
        api_or_compute_cost=Decimal("5"),
        license_cost=Decimal("10"),
    )

    assert result == Decimal("685")


def test_api_cost_uses_fresh_cached_output_and_batch_discount() -> None:
    pricing = estimate_run_cost.ModelPricing(
        name="test",
        input_per_million=Decimal("1"),
        cached_input_per_million=Decimal("0.10"),
        output_per_million=Decimal("10"),
        batch_discount_multiplier=Decimal("0.50"),
    )

    result = estimate_run_cost.api_cost_usd(
        pricing,
        input_tokens=1_000_000,
        cached_input_tokens=250_000,
        output_tokens=100_000,
        uses_batch_discount=True,
    )

    assert result == Decimal("0.8875")


def test_default_scenarios_have_ordered_sensitivity_ranges() -> None:
    rows = estimate_run_cost.build_rows()

    assert [row["scenario"] for row in rows] == [
        "10-PDF evidence packet",
        "30-PDF project evidence scan",
        "Systematic-review pre-screening",
    ]
    for row in rows:
        low = Decimal(row["net_savings_low_usd"])
        base = Decimal(row["net_savings_base_usd"])
        high = Decimal(row["net_savings_high_usd"])
        assert low <= base <= high


def test_generated_csv_has_stable_report_columns(tmp_path: Path) -> None:
    rows = estimate_run_cost.build_rows()
    csv_path = tmp_path / "cost_benefit.csv"

    estimate_run_cost.write_csv(csv_path, rows)

    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        loaded_rows = list(reader)

    assert reader.fieldnames == estimate_run_cost.CSV_FIELDS
    assert len(loaded_rows) == 3
    assert {
        "scenario",
        "paper_count",
        "assumed_query_run_count",
        "input_tokens",
        "output_tokens",
        "api_or_compute_cost_usd",
        "manual_hours_low",
        "manual_hours_base",
        "manual_hours_high",
        "papermemory_operation_hours",
        "verification_hours_low",
        "verification_hours_base",
        "verification_hours_high",
        "labor_profile",
        "fully_loaded_hourly_rate_usd",
        "license_cost_usd",
        "net_savings_low_usd",
        "net_savings_base_usd",
        "net_savings_high_usd",
        "source_notes",
    }.issubset(set(reader.fieldnames or []))
