from __future__ import annotations

import app
from config import Settings
from models import Finding, FindingCategory


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
        gmail_recipient="owner@example.com",
        gmail_token_json=None,
        whatsapp_access_token=None,
        whatsapp_phone_number_id=None,
        whatsapp_to=None,
        whatsapp_api_version="v19.0",
    )


class FakeFactory:
    def __init__(self, region_name: str) -> None:
        self.region_name = region_name


def test_run_guardrail_returns_partial_results_when_detector_fails(monkeypatch) -> None:
    def idle_detector(factory, loaded_settings):
        return [
            Finding(
                category=FindingCategory.UNATTACHED_EBS,
                resource_id="vol-001",
                resource_type="ebs-volume",
                region=loaded_settings.aws_region,
                title="Unattached EBS volume: vol-001",
                description="Detached volume",
                metric_name="age_days",
                metric_value=10,
                threshold=0,
            )
        ]

    def failing_detector(factory, loaded_settings):
        raise RuntimeError("Cost Explorer is not enabled")

    monkeypatch.setattr(app, "AwsClientFactory", FakeFactory)
    monkeypatch.setattr(app, "detect_idle_resources", idle_detector)
    monkeypatch.setattr(app, "detect_spend_spikes", failing_detector)
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(settings(), send_alerts=False)

    assert response["finding_count"] == 1
    assert response["recommendation_count"] == 1
    assert response["errors"] == [
        {
            "detector": "spend_spikes",
            "error_type": "RuntimeError",
            "message": "Cost Explorer is not enabled",
        }
    ]
