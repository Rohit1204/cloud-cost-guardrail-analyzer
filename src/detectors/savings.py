from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from aws_clients import AwsClientFactory
from config import Settings
from models import Finding, FindingCategory
from ownership import resolve_owner_email


def _service_total(results: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for result in results:
        for group in result.get("Groups", []):
            service = group.get("Keys", ["Unknown"])[0]
            amount = float(group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0.0))
            totals[service] = totals.get(service, 0.0) + amount
    return totals


def detect_high_cost_services(factory: AwsClientFactory, settings: Settings) -> list[Finding]:
    today = date.today()
    start = today - timedelta(days=settings.lookback_days)
    results = factory.daily_unblended_costs(
        start=start.isoformat(),
        end=today.isoformat(),
        group_by_service=True,
    )
    findings: list[Finding] = []
    for service, total in sorted(_service_total(results).items(), key=lambda item: item[1], reverse=True):
        if total < settings.high_cost_service_threshold_usd:
            continue
        findings.append(
            Finding(
                category=FindingCategory.HIGH_COST_SERVICE,
                resource_id=service,
                resource_type="aws-service",
                region="global",
                title=f"High spend service: {service}",
                description=(
                    f"{service} spent ${total:.2f} over the last {settings.lookback_days} days, "
                    f"above the ${settings.high_cost_service_threshold_usd:.2f} review threshold."
                ),
                metric_name="UnblendedCost",
                metric_value=total,
                threshold=settings.high_cost_service_threshold_usd,
                metadata={
                    "lookback_days": settings.lookback_days,
                    "environment": settings.default_environment,
                    "owner_email": resolve_owner_email(None, settings.default_environment, settings),
                },
            )
        )
    return findings


def detect_savings_opportunities(factory: AwsClientFactory, settings: Settings) -> list[Finding]:
    return detect_high_cost_services(factory, settings)
