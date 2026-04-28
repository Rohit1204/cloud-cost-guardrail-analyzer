from __future__ import annotations

from config import Settings
from models import Finding, FindingCategory
from notifiers.gmail import _group_by_recipient
from recommendations import recommendation_for


def settings() -> Settings:
    return Settings(
        aws_region="ap-south-1",
        lookback_days=7,
        idle_cpu_threshold=5,
        idle_db_connection_threshold=1,
        spend_spike_multiplier=1.5,
        spend_spike_min_usd=25,
        high_cost_service_threshold_usd=100,
        alert_channels=("gmail",),
        gmail_sender="me",
        gmail_recipient="default@example.com",
        allowed_alert_recipients=("default@example.com",),
        gmail_token_json={"token": "fake"},
        owner_tag_keys=("OwnerEmail", "Owner", "Team"),
        environment_tag_keys=("Environment", "Env"),
        owner_email_map={},
        default_owner_email=None,
        default_environment=None,
        recommendation_status_table=None,
        google_client_id=None,
        auth_allowed_emails=("default@example.com",),
        whatsapp_access_token=None,
        whatsapp_phone_number_id=None,
        whatsapp_to=None,
        whatsapp_api_version="v19.0",
    )


def test_group_by_recipient_routes_recommendations_to_owner_email() -> None:
    platform_finding = Finding(
        category=FindingCategory.IDLE_EC2,
        resource_id="i-platform",
        resource_type="ec2-instance",
        region="ap-south-1",
        title="Idle EC2 instance: platform",
        description="Idle platform instance",
        metric_name="CPUUtilization",
        metric_value=1,
        threshold=5,
        metadata={"owner_email": "platform@example.com"},
    )
    unowned_finding = Finding(
        category=FindingCategory.UNATTACHED_EBS,
        resource_id="vol-001",
        resource_type="ebs-volume",
        region="ap-south-1",
        title="Unattached EBS volume: vol-001",
        description="Detached volume",
        metric_name="age_days",
        metric_value=10,
        threshold=0,
    )

    grouped = _group_by_recipient(
        [recommendation_for(platform_finding), recommendation_for(unowned_finding)],
        settings(),
    )

    assert set(grouped) == {"platform@example.com", "default@example.com"}
    assert grouped["platform@example.com"][0].finding.resource_id == "i-platform"
    assert grouped["default@example.com"][0].finding.resource_id == "vol-001"
