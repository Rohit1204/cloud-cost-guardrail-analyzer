from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from aws_clients import AwsClientFactory
from config import Settings
from models import Finding, FindingCategory
from ownership import resolve_owner_email


def _amount(result: dict[str, Any]) -> float:
    return float(result.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0.0))


def _top_services(results: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    currency = "USD"
    for result in results:
        for group in result.get("Groups", []):
            service = group.get("Keys", ["Unknown"])[0]
            metric = group.get("Metrics", {}).get("UnblendedCost", {})
            amount = float(metric.get("Amount", 0.0))
            currency = metric.get("Unit", currency)
            totals[service] = totals.get(service, 0.0) + amount
    return [
        {"service": service, "amount": round(amount, 4), "currency": currency}
        for service, amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
        if amount > 0
    ]


def detect_spend_spikes(factory: AwsClientFactory, settings: Settings) -> list[Finding]:
    today = date.today()
    start = today - timedelta(days=settings.lookback_days + 1)
    results = factory.daily_unblended_costs(start=start.isoformat(), end=today.isoformat())
    daily_costs = [_amount(result) for result in results]
    if len(daily_costs) < 2:
        return []

    latest = daily_costs[-1]
    baseline_values = daily_costs[:-1]
    baseline = sum(baseline_values) / len(baseline_values)
    increase = latest - baseline
    if latest < settings.spend_spike_min_usd:
        return []
    if baseline > 0 and latest < baseline * settings.spend_spike_multiplier:
        return []
    if baseline == 0 and latest < settings.spend_spike_min_usd:
        return []

    latest_day = today - timedelta(days=1)
    latest_service_results = factory.daily_unblended_costs(
        start=latest_day.isoformat(),
        end=today.isoformat(),
        group_by_service=True,
    )

    return [
        Finding(
            category=FindingCategory.SPEND_SPIKE,
            resource_id="aws-account",
            resource_type="aws-cost",
            region="global",
            title="AWS daily spend spike detected",
            description=(
                f"Latest daily spend is ${latest:.2f}, compared with a "
                f"${baseline:.2f} daily baseline."
            ),
            metric_name="UnblendedCost",
            metric_value=latest,
            threshold=max(settings.spend_spike_min_usd, baseline * settings.spend_spike_multiplier),
            estimated_monthly_savings=max(increase, 0.0) * 30,
            metadata={
                "baseline_daily_cost": baseline,
                "increase": increase,
                "top_services": _top_services(latest_service_results),
                "environment": settings.default_environment,
                "owner_email": resolve_owner_email(None, settings.default_environment, settings),
            },
        )
    ]
