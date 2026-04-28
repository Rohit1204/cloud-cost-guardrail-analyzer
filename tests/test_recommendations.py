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
        metadata={
            "baseline_daily_cost": 75,
            "increase": 175,
            "top_services": [
                {"service": "Amazon Elastic Compute Cloud - Compute", "amount": 180, "currency": "USD"}
            ],
        },
    )

    recommendation = recommendation_for(finding)

    assert recommendation.priority == Priority.CRITICAL
    assert "Investigate" in recommendation.action
    assert "Amazon Elastic Compute Cloud" in recommendation.rationale
    assert any("Cost Explorer" in step for step in recommendation.next_steps)


def test_high_cost_ec2_recommendation_uses_service_specific_playbook() -> None:
    finding = Finding(
        category=FindingCategory.HIGH_COST_SERVICE,
        resource_id="Amazon Elastic Compute Cloud - Compute",
        resource_type="aws-service",
        region="global",
        title="High spend service: Amazon Elastic Compute Cloud - Compute",
        description="EC2 crossed threshold",
        metric_name="UnblendedCost",
        metric_value=250,
        threshold=100,
        metadata={"lookback_days": 7, "owner_email": "platform@example.com"},
    )

    recommendation = recommendation_for(finding)

    assert recommendation.priority == Priority.WARNING
    assert "EC2" in recommendation.action
    assert any("Compute Optimizer" in step for step in recommendation.next_steps)
    assert any("Savings Plans" in step for step in recommendation.next_steps)


def test_idle_production_ec2_recommendation_avoids_immediate_stop() -> None:
    finding = Finding(
        category=FindingCategory.IDLE_EC2,
        resource_id="i-prod",
        resource_type="ec2-instance",
        region="ap-south-1",
        title="Idle EC2 instance: api-prod",
        description="Low CPU",
        metric_name="CPUUtilization",
        metric_value=2,
        threshold=5,
        metadata={"instance_type": "m6i.large", "environment": "prod", "owner": "api"},
    )

    recommendation = recommendation_for(finding)

    assert "production" in recommendation.action
    assert "downsize" in recommendation.action
