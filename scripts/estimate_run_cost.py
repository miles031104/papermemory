from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "reports" / "final" / "results"
DEFAULT_CSV_PATH = RESULTS_DIR / "cost_benefit.csv"
DEFAULT_MARKDOWN_PATH = RESULTS_DIR / "cost_benefit.md"

SOURCE_SNAPSHOT_DATE = "2026-06-24"
ANNUAL_HOURS_DIVISOR = Decimal("2080")
FULLY_LOADED_MULTIPLIER = Decimal("1.35")
MONEY = Decimal("0.01")
TOKEN_DENOMINATOR = Decimal("1000000")

SOURCE_URLS = {
    "openai_pricing": "https://openai.com/api/pricing/",
    "bls_management_analysts": "https://www.bls.gov/ooh/business-and-financial/management-analysts.htm",
    "bls_data_scientists": "https://www.bls.gov/ooh/math/data-scientists.htm",
    "bls_medical_scientists": "https://www.bls.gov/ooh/life-physical-and-social-science/medical-scientists.htm",
    "elicit_pricing": "https://elicit.com/pricing",
    "consensus_plans": "https://help.consensus.app/en/articles/10087865-subscription-plans",
}

CSV_FIELDS = [
    "scenario",
    "paper_count",
    "assumed_query_run_count",
    "model",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "uses_batch_discount",
    "api_or_compute_cost_usd",
    "manual_hours_low",
    "manual_hours_base",
    "manual_hours_high",
    "papermemory_operation_hours",
    "verification_hours_low",
    "verification_hours_base",
    "verification_hours_high",
    "labor_profile",
    "annual_wage_usd",
    "wage_source_url",
    "fully_loaded_hourly_rate_usd",
    "license_cost_usd",
    "net_savings_low_usd",
    "net_savings_base_usd",
    "net_savings_high_usd",
    "source_notes",
]


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def decimal_text(value: Decimal, places: int = 2) -> str:
    quantum = Decimal("1").scaleb(-places)
    return str(value.quantize(quantum, rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class ModelPricing:
    name: str
    input_per_million: Decimal
    cached_input_per_million: Decimal
    output_per_million: Decimal
    batch_discount_multiplier: Decimal = Decimal("0.50")


@dataclass(frozen=True)
class LaborProfile:
    name: str
    median_annual_wage_usd: Decimal
    source_url: str


@dataclass(frozen=True)
class ScenarioAssumption:
    name: str
    paper_count: int
    assumed_query_run_count: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    uses_batch_discount: bool
    manual_hours_low: Decimal
    manual_hours_base: Decimal
    manual_hours_high: Decimal
    papermemory_operation_hours: Decimal
    verification_hours_low: Decimal
    verification_hours_base: Decimal
    verification_hours_high: Decimal
    labor_profile: str
    license_cost_usd: Decimal
    source_notes: str


DEFAULT_PRICING = ModelPricing(
    name="GPT-5.4 mini",
    input_per_million=Decimal("0.75"),
    cached_input_per_million=Decimal("0.075"),
    output_per_million=Decimal("4.50"),
)

DEFAULT_LABOR_PROFILES = {
    "management_analyst": LaborProfile(
        name="BLS management analysts",
        median_annual_wage_usd=Decimal("101190"),
        source_url=SOURCE_URLS["bls_management_analysts"],
    ),
    "data_scientist": LaborProfile(
        name="BLS data scientists",
        median_annual_wage_usd=Decimal("112590"),
        source_url=SOURCE_URLS["bls_data_scientists"],
    ),
    "medical_scientist": LaborProfile(
        name="BLS medical scientists",
        median_annual_wage_usd=Decimal("100590"),
        source_url=SOURCE_URLS["bls_medical_scientists"],
    ),
}

DEFAULT_SCENARIOS = [
    ScenarioAssumption(
        name="10-PDF evidence packet",
        paper_count=10,
        assumed_query_run_count=3,
        input_tokens=175_000,
        cached_input_tokens=25_000,
        output_tokens=17_500,
        uses_batch_discount=False,
        manual_hours_low=Decimal("2.5"),
        manual_hours_base=Decimal("4.0"),
        manual_hours_high=Decimal("6.0"),
        papermemory_operation_hours=Decimal("0.4"),
        verification_hours_low=Decimal("0.5"),
        verification_hours_base=Decimal("0.8"),
        verification_hours_high=Decimal("1.3"),
        labor_profile="management_analyst",
        license_cost_usd=Decimal("0.00"),
        source_notes=(
            "Routine postgraduate evidence-packet run scaled from the original "
            "Node 9 planning estimate; license cost left at 0 pending "
            "deployment-specific MuPDF/PyMuPDF licensing decision."
        ),
    ),
    ScenarioAssumption(
        name="30-PDF project evidence scan",
        paper_count=30,
        assumed_query_run_count=6,
        input_tokens=690_000,
        cached_input_tokens=120_000,
        output_tokens=54_000,
        uses_batch_discount=False,
        manual_hours_low=Decimal("7.2"),
        manual_hours_base=Decimal("12.0"),
        manual_hours_high=Decimal("19.2"),
        papermemory_operation_hours=Decimal("1.1"),
        verification_hours_low=Decimal("1.8"),
        verification_hours_base=Decimal("3.0"),
        verification_hours_high=Decimal("4.8"),
        labor_profile="data_scientist",
        license_cost_usd=Decimal("15.00"),
        source_notes=(
            "Routine project-scan planning placeholder scaled from the original "
            "Node 9 estimate; not based on PaperMemory production telemetry."
        ),
    ),
    ScenarioAssumption(
        name="Systematic-review pre-screening",
        paper_count=200,
        assumed_query_run_count=10,
        input_tokens=3_500_000,
        cached_input_tokens=750_000,
        output_tokens=250_000,
        uses_batch_discount=True,
        manual_hours_low=Decimal("40.0"),
        manual_hours_base=Decimal("80.0"),
        manual_hours_high=Decimal("140.0"),
        papermemory_operation_hours=Decimal("6.0"),
        verification_hours_low=Decimal("12.0"),
        verification_hours_base=Decimal("20.0"),
        verification_hours_high=Decimal("36.0"),
        labor_profile="medical_scientist",
        license_cost_usd=Decimal("100.00"),
        source_notes=(
            "Pre-screening estimate only; this is not a claim that PaperMemory "
            "replaces a systematic-review protocol or adjudication workflow."
        ),
    ),
]


def api_cost_usd(
    pricing: ModelPricing,
    *,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    uses_batch_discount: bool = False,
) -> Decimal:
    if min(input_tokens, output_tokens, cached_input_tokens) < 0:
        raise ValueError("token counts must be non-negative")
    if cached_input_tokens > input_tokens:
        raise ValueError("cached input tokens cannot exceed input tokens")

    fresh_input_tokens = input_tokens - cached_input_tokens
    cost = (
        Decimal(fresh_input_tokens) * pricing.input_per_million
        + Decimal(cached_input_tokens) * pricing.cached_input_per_million
        + Decimal(output_tokens) * pricing.output_per_million
    ) / TOKEN_DENOMINATOR
    if uses_batch_discount:
        cost *= pricing.batch_discount_multiplier
    return cost


def hourly_rate_from_annual_wage(
    annual_wage_usd: Decimal,
    *,
    annual_hours_divisor: Decimal = ANNUAL_HOURS_DIVISOR,
    fully_loaded_multiplier: Decimal = FULLY_LOADED_MULTIPLIER,
) -> Decimal:
    if annual_wage_usd <= 0:
        raise ValueError("annual wage must be positive")
    if annual_hours_divisor <= 0:
        raise ValueError("annual hours divisor must be positive")
    if fully_loaded_multiplier <= 0:
        raise ValueError("fully loaded multiplier must be positive")
    return annual_wage_usd / annual_hours_divisor * fully_loaded_multiplier


def net_savings_usd(
    *,
    manual_hours: Decimal,
    papermemory_hours: Decimal,
    verification_hours: Decimal,
    fully_loaded_hourly_rate: Decimal,
    api_or_compute_cost: Decimal,
    license_cost: Decimal,
) -> Decimal:
    saved_labor = (manual_hours - papermemory_hours - verification_hours) * fully_loaded_hourly_rate
    return saved_labor - api_or_compute_cost - license_cost


def scenario_to_row(
    scenario: ScenarioAssumption,
    *,
    pricing: ModelPricing = DEFAULT_PRICING,
    labor_profiles: dict[str, LaborProfile] = DEFAULT_LABOR_PROFILES,
) -> dict[str, str]:
    labor = labor_profiles[scenario.labor_profile]
    hourly_rate = hourly_rate_from_annual_wage(labor.median_annual_wage_usd)
    api_cost = api_cost_usd(
        pricing,
        input_tokens=scenario.input_tokens,
        output_tokens=scenario.output_tokens,
        cached_input_tokens=scenario.cached_input_tokens,
        uses_batch_discount=scenario.uses_batch_discount,
    )
    low = net_savings_usd(
        manual_hours=scenario.manual_hours_low,
        papermemory_hours=scenario.papermemory_operation_hours,
        verification_hours=scenario.verification_hours_high,
        fully_loaded_hourly_rate=hourly_rate,
        api_or_compute_cost=api_cost,
        license_cost=scenario.license_cost_usd,
    )
    base = net_savings_usd(
        manual_hours=scenario.manual_hours_base,
        papermemory_hours=scenario.papermemory_operation_hours,
        verification_hours=scenario.verification_hours_base,
        fully_loaded_hourly_rate=hourly_rate,
        api_or_compute_cost=api_cost,
        license_cost=scenario.license_cost_usd,
    )
    high = net_savings_usd(
        manual_hours=scenario.manual_hours_high,
        papermemory_hours=scenario.papermemory_operation_hours,
        verification_hours=scenario.verification_hours_low,
        fully_loaded_hourly_rate=hourly_rate,
        api_or_compute_cost=api_cost,
        license_cost=scenario.license_cost_usd,
    )

    return {
        "scenario": scenario.name,
        "paper_count": str(scenario.paper_count),
        "assumed_query_run_count": str(scenario.assumed_query_run_count),
        "model": pricing.name,
        "input_tokens": str(scenario.input_tokens),
        "cached_input_tokens": str(scenario.cached_input_tokens),
        "output_tokens": str(scenario.output_tokens),
        "uses_batch_discount": str(scenario.uses_batch_discount).lower(),
        "api_or_compute_cost_usd": decimal_text(money(api_cost)),
        "manual_hours_low": decimal_text(scenario.manual_hours_low, places=1),
        "manual_hours_base": decimal_text(scenario.manual_hours_base, places=1),
        "manual_hours_high": decimal_text(scenario.manual_hours_high, places=1),
        "papermemory_operation_hours": decimal_text(scenario.papermemory_operation_hours, places=1),
        "verification_hours_low": decimal_text(scenario.verification_hours_low, places=1),
        "verification_hours_base": decimal_text(scenario.verification_hours_base, places=1),
        "verification_hours_high": decimal_text(scenario.verification_hours_high, places=1),
        "labor_profile": labor.name,
        "annual_wage_usd": decimal_text(labor.median_annual_wage_usd),
        "wage_source_url": labor.source_url,
        "fully_loaded_hourly_rate_usd": decimal_text(money(hourly_rate)),
        "license_cost_usd": decimal_text(money(scenario.license_cost_usd)),
        "net_savings_low_usd": decimal_text(money(low)),
        "net_savings_base_usd": decimal_text(money(base)),
        "net_savings_high_usd": decimal_text(money(high)),
        "source_notes": scenario.source_notes,
    }


def build_rows(scenarios: Iterable[ScenarioAssumption] = DEFAULT_SCENARIOS) -> list[dict[str, str]]:
    return [scenario_to_row(scenario) for scenario in scenarios]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def rows_to_csv_text(rows: list[dict[str, str]]) -> str:
    from io import StringIO

    handle = StringIO()
    writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_markdown(rows: list[dict[str, str]]) -> str:
    assumption_rows = [
        [
            row["scenario"],
            row["paper_count"],
            row["assumed_query_run_count"],
            row["input_tokens"],
            row["cached_input_tokens"],
            row["output_tokens"],
            row["api_or_compute_cost_usd"],
            row["license_cost_usd"],
        ]
        for row in rows
    ]
    sensitivity_rows = [
        [
            row["scenario"],
            row["manual_hours_low"],
            row["manual_hours_base"],
            row["manual_hours_high"],
            row["papermemory_operation_hours"],
            row["verification_hours_low"],
            row["verification_hours_base"],
            row["verification_hours_high"],
            row["fully_loaded_hourly_rate_usd"],
            row["net_savings_low_usd"],
            row["net_savings_base_usd"],
            row["net_savings_high_usd"],
        ]
        for row in rows
    ]
    interpretation_lines = "\n".join(
        f"- **{row['scenario']}**: base-case net savings is `${row['net_savings_base_usd']}` "
        f"after PaperMemory operation time, human verification time, API/compute cost, and "
        f"the scenario license-cost assumption. Low/high cases are `${row['net_savings_low_usd']}` "
        f"to `${row['net_savings_high_usd']}`."
        for row in rows
    )
    row_by_name = {row["scenario"]: row for row in rows}
    light_cost = Decimal(row_by_name["10-PDF evidence packet"]["api_or_compute_cost_usd"])
    heavier_cost = Decimal(row_by_name["30-PDF project evidence scan"]["api_or_compute_cost_usd"])
    light_month = money(light_cost * Decimal("4"))
    heavier_month = money(heavier_cost * Decimal("4"))
    heavy_guard_month = money(heavier_cost * Decimal("8"))
    light_headroom = money(Decimal("10.00") - light_month)
    heavier_headroom = money(Decimal("20.00") - heavier_month)
    heavy_guard_headroom = money(Decimal("20.00") - heavy_guard_month)

    return f"""# Node 9 Cost-Benefit Stress Test

This artifact is generated by `python scripts/estimate_run_cost.py --write-reports`.
All values are planning estimates unless they come from the cited pricing or wage source snapshot.

## Formula

```text
net_savings = (manual_hours - papermemory_hours - verification_hours) * fully_loaded_hourly_rate - api_or_compute_cost - license_cost
```

Low/base/high sensitivity is computed as:

- Low: low manual hours and high verification hours.
- Base: base manual hours and base verification hours.
- High: high manual hours and low verification hours.

## Source Snapshot

Snapshot date: {SOURCE_SNAPSHOT_DATE}

- OpenAI API pricing: [{SOURCE_URLS['openai_pricing']}]({SOURCE_URLS['openai_pricing']}). The stage snapshot records {DEFAULT_PRICING.name} at `${DEFAULT_PRICING.input_per_million}` input / 1M tokens, `${DEFAULT_PRICING.cached_input_per_million}` cached input / 1M tokens, and `${DEFAULT_PRICING.output_per_million}` output / 1M tokens. The Batch API discount is modeled as 50% when `uses_batch_discount=true`.
- BLS management analysts wage source: [{SOURCE_URLS['bls_management_analysts']}]({SOURCE_URLS['bls_management_analysts']}).
- BLS data scientists wage source: [{SOURCE_URLS['bls_data_scientists']}]({SOURCE_URLS['bls_data_scientists']}).
- BLS medical scientists wage source: [{SOURCE_URLS['bls_medical_scientists']}]({SOURCE_URLS['bls_medical_scientists']}).
- Elicit pricing: [{SOURCE_URLS['elicit_pricing']}]({SOURCE_URLS['elicit_pricing']}) as market context only.
- Consensus subscription plans: [{SOURCE_URLS['consensus_plans']}]({SOURCE_URLS['consensus_plans']}) as market context only.

Labor conversion uses annual wage / {ANNUAL_HOURS_DIVISOR} hours * {FULLY_LOADED_MULTIPLIER} fully loaded multiplier.

## Scenario Assumptions

{markdown_table(
        [
            "Scenario",
            "PDFs",
            "Runs",
            "Input tokens",
            "Cached input tokens",
            "Output tokens",
            "API/compute cost USD",
            "License cost USD",
        ],
        assumption_rows,
    )}

## Sensitivity Results

{markdown_table(
        [
            "Scenario",
            "Manual low",
            "Manual base",
            "Manual high",
            "PaperMemory hours",
            "Verify low",
            "Verify base",
            "Verify high",
            "Loaded rate USD/hr",
            "Net low USD",
            "Net base USD",
            "Net high USD",
        ],
        sensitivity_rows,
    )}

## Interpretation

{interpretation_lines}

The result is a commercial stress test, not a guarantee of ROI. PaperMemory should be positioned around first-pass evidence gathering, citation packaging, and human verification. The systematic-review pre-screening scenario is explicitly a pre-screening estimate, not a claim that PaperMemory replaces a systematic-review protocol or adjudication workflow.

Elicit and Consensus pricing are included only as market context. They are not treated as direct feature-parity benchmarks for PaperMemory.

## Tier Economics Assumption

The 10 USD/month and 20 USD/month tiers are proposed planning assumptions, not validated pricing telemetry. They assume provider-compliant API relay or commercial API access for PaperMemory-managed LLM support, qualitative weekly caps, BYOK fallback above cap, rate limits, and fair-use controls. The model does not assume consumer-account pooling, subscription resale, unlimited inference, or validated production margins.

### Illustrative Managed-Access Sensitivity

The tier table uses the routine 10-PDF and 30-PDF scenario costs as illustrative planning stress cases. A modeled 10 USD/month light-use month assumes four 10-PDF evidence-packet runs at {light_cost} USD each, for 4 x {light_cost} = {light_month} USD of API/compute cost and {light_headroom} USD of revenue headroom before hosting, support, licensing, abuse monitoring, payment costs, and human verification overhead. A modeled 20 USD/month heavier-use month assumes four 30-PDF evidence-scan runs at {heavier_cost} USD each, for 4 x {heavier_cost} = {heavier_month} USD of API/compute cost and {heavier_headroom} USD of headroom before those non-model costs. An eight-run heavy-use guard assumes 8 x {heavier_cost} = {heavy_guard_month} USD of API/compute cost and leaves {heavy_guard_headroom} USD before non-model costs at the 20 USD price, but it shows why the product must use weekly caps, rate limits, BYOK fallback, fair-use controls, or add-ons instead of unlimited inference.

These rows are illustrative stress cases, not production quotas, validated margins, production telemetry, validated revenue, or customer usage telemetry.

## Commercial Deployment Risks

- PyMuPDF is distributed under the MuPDF licensing model, including AGPL obligations unless a commercial license is appropriate. Any commercial PaperMemory deployment that uses PyMuPDF/MuPDF needs legal and licensing review before these estimates can be converted into production margins.
- Customer willingness to pay, sales cycle, support cost, hosting cost, and usage variance are not validated by this Node 9 artifact.
- The OpenAI, BLS, Elicit, and Consensus values are from the {SOURCE_SNAPSHOT_DATE} stage-plan snapshot and should be refreshed before investor/customer-facing use.
"""


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown(rows), encoding="utf-8", newline="\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate PaperMemory per-run cost and labor savings.")
    parser.add_argument("--write-reports", action="store_true", help="write CSV and Markdown artifacts")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--markdown-path", type=Path, default=DEFAULT_MARKDOWN_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    rows = build_rows()
    if args.write_reports:
        write_csv(args.csv_path, rows)
        write_markdown(args.markdown_path, rows)
        print(f"wrote {args.csv_path}")
        print(f"wrote {args.markdown_path}")
        return 0

    print(rows_to_csv_text(rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
