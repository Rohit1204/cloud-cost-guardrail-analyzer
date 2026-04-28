from __future__ import annotations

from models import Finding, FindingCategory, Priority
from recommendations import recommendation_for


def test_unattached_ebs_recommendation_includes_snapshot_and_delete_steps() -> None:
    finding = Finding(
        category=FindingCategory.UNATTACHED_EBS,
        resource_id="vol-123",
        resource_type="ebs-volume",
        region="us-east-1",
        title="Unattached EBS volume: vol-123",
        description="Detached volume",
        metric_name="age_days",
        metric_value=12,
        threshold=0,
        estimated_monthly_savings=8.0,
    )

    recommendation = recommendation_for(finding)

    assert recommendation.priority == Priority.WARNING
    assert "Snapshot" in recommendation.action
    assert any("create-snapshot" in step for step in recommendation.next_steps)
    assert any("delete-volume" in step for step in recommendation.next_steps)


def test_spend_spike_recommendation_is_critical_and_actionable() -> None:
    finding = Finding(
        category=FindingCategory.SPEND_SPIKE,
        resource_id="aws-account",
        resource_type="aws-cost",
        region="global",
        title="AWS daily spend spike detected",
        description="Latest spend exceeded baseline",
        metric_name="UnblendedCost",
        metric_value=250,
        threshold=100,
    )

    recommendation = recommendation_for(finding)

    assert recommendation.priority == Priority.CRITICAL
    assert "Investigate" in recommendation.action
    assert any("Cost Explorer" in step for step in recommendation.next_steps)
