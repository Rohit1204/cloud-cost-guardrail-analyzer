from __future__ import annotations

from models import Finding, FindingCategory
from notifiers.message_builder import build_body, build_subject
from recommendations import recommendation_for


def test_message_builder_formats_recommendation_with_next_steps() -> None:
    finding = Finding(
        category=FindingCategory.IDLE_EC2,
        resource_id="i-abc123",
        resource_type="ec2-instance",
        region="us-east-1",
        title="Idle EC2 instance: api-dev",
        description="Instance averaged 2.1% CPU over 7 days.",
        metric_name="CPUUtilization",
        metric_value=2.1,
        threshold=5,
        metadata={
            "instance_type": "t3.medium",
            "owner": "platform",
            "owner_email": "platform@example.com",
            "environment": "dev",
        },
    )
    recommendation = recommendation_for(finding)

    subject = build_subject([recommendation])
    body = build_body([recommendation])

    assert "1 findings" in subject
    assert "Idle EC2 instance" in body
    assert "Owner route: platform / platform@example.com" in body
    assert "Environment: dev" in body
    assert "aws ec2 stop-instances" in body
