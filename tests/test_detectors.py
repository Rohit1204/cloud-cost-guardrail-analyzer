from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import Settings
from detectors.idle_resources import detect_unattached_ebs
from detectors.spend_spikes import detect_spend_spikes
from models import FindingCategory


def settings() -> Settings:
    return Settings(
        aws_region="us-east-1",
        lookback_days=7,
        idle_cpu_threshold=5,
        idle_db_connection_threshold=1,
        spend_spike_multiplier=1.5,
        spend_spike_min_usd=25,
        high_cost_service_threshold_usd=100,
        alert_channels=("gmail", "whatsapp"),
        gmail_sender="me",
        gmail_recipient="owner@example.com",
        gmail_token_json=None,
        whatsapp_access_token=None,
        whatsapp_phone_number_id=None,
        whatsapp_to=None,
        whatsapp_api_version="v19.0",
    )


class FakeCostFactory:
    def __init__(self, amounts: list[float]) -> None:
        self.amounts = amounts

    def daily_unblended_costs(self, **kwargs):
        return [
            {"Total": {"UnblendedCost": {"Amount": str(amount)}}}
            for amount in self.amounts
        ]


class FakeVolumeFactory:
    def list_unattached_volumes(self):
        return [
            {
                "VolumeId": "vol-001",
                "CreateTime": datetime.now(timezone.utc) - timedelta(days=10),
                "Size": 100,
                "VolumeType": "gp3",
                "AvailabilityZone": "us-east-1a",
            }
        ]


def test_spend_spike_detector_requires_threshold_breach() -> None:
    findings = detect_spend_spikes(FakeCostFactory([10, 12, 11, 13, 10, 12, 11, 40]), settings())

    assert len(findings) == 1
    assert findings[0].category == FindingCategory.SPEND_SPIKE
    assert findings[0].estimated_monthly_savings is not None


def test_spend_spike_detector_ignores_small_increase() -> None:
    findings = detect_spend_spikes(FakeCostFactory([10, 12, 11, 13, 10, 12, 11, 15]), settings())

    assert findings == []


def test_unattached_ebs_detector_estimates_monthly_savings() -> None:
    findings = detect_unattached_ebs(FakeVolumeFactory(), settings())

    assert len(findings) == 1
    assert findings[0].resource_id == "vol-001"
    assert findings[0].estimated_monthly_savings == 8.0
