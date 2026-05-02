from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from billing_console import billing_console_federation_url
from config import Settings


def _minimal_settings(role_arn: str | None) -> Settings:
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
        allowed_alert_recipients=("owner@example.com",),
        gmail_token_json=None,
        owner_tag_keys=("OwnerEmail",),
        environment_tag_keys=("Environment",),
        owner_email_map={},
        default_owner_email=None,
        default_environment=None,
        recommendation_status_table=None,
        google_client_id=None,
        auth_allowed_emails=("owner@example.com",),
        whatsapp_access_token=None,
        whatsapp_phone_number_id=None,
        whatsapp_to=None,
        whatsapp_api_version="v19.0",
        billing_console_role_arn=role_arn,
    )


def test_billing_console_requires_role_arn() -> None:
    with pytest.raises(ValueError, match="not configured"):
        billing_console_federation_url(_minimal_settings(None), {"email": "a@b.com"})


def test_billing_console_builds_federation_url(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sts = MagicMock()
    fake_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIATEST",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        }
    }
    monkeypatch.setattr("billing_console.boto3.client", lambda service_name, **kwargs: fake_sts if service_name == "sts" else MagicMock())

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"SigninToken": "signin-token"}

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())

    url = billing_console_federation_url(
        _minimal_settings("arn:aws:iam::123456789012:role/test-billing"),
        {"email": "owner@example.com"},
    )

    assert "signin.aws.amazon.com/federation" in url
    assert "SigninToken=signin-token" in url
    assert "Destination=" in url
    fake_sts.assume_role.assert_called_once()
