from __future__ import annotations

from models import Recommendation


def build_subject(recommendations: list[Recommendation]) -> str:
    if not recommendations:
        return "Cloud Cost Guardrail: no findings"
    critical = sum(1 for item in recommendations if item.priority.value == "critical")
    warning = sum(1 for item in recommendations if item.priority.value == "warning")
    return f"Cloud Cost Guardrail: {len(recommendations)} findings ({critical} critical, {warning} warning)"


def build_body(recommendations: list[Recommendation]) -> str:
    if not recommendations:
        return "Cloud Cost Guardrail found no idle resources, spend spikes, or savings opportunities in this run."

    lines = [build_subject(recommendations), ""]
    for index, recommendation in enumerate(recommendations, start=1):
        finding = recommendation.finding
        savings = ""
        if finding.estimated_monthly_savings is not None:
            savings = f"\nEstimated savings: ${finding.estimated_monthly_savings:.2f}/month"
        lines.extend(
            [
                f"{index}. [{recommendation.priority.value.upper()}] {finding.title}",
                f"Resource: {finding.resource_type} / {finding.resource_id} ({finding.region})",
                f"Why: {finding.description}",
                f"Action: {recommendation.action}",
                f"Rationale: {recommendation.rationale}{savings}",
                "Next steps:",
                *(f"- {step}" for step in recommendation.next_steps),
                "",
            ]
        )
    return "\n".join(lines).strip()
