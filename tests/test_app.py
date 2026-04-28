from __future__ import annotations

import json
from dataclasses import replace

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
        allowed_alert_recipients=("owner@example.com", "team@example.com"),
        gmail_token_json=None,
        owner_tag_keys=("OwnerEmail", "Owner", "Team"),
        environment_tag_keys=("Environment", "Env"),
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
    )


class FakeFactory:
    def __init__(self, region_name: str) -> None:
        self.region_name = region_name

    def monthly_unblended_costs(self, **kwargs):
        if kwargs.get("group_by_service"):
            return [
                {
                    "TimePeriod": {"Start": "2026-04-01", "End": "2026-04-29"},
                    "Groups": [
                        {"Keys": ["Amazon Elastic Compute Cloud - Compute"], "Metrics": {"UnblendedCost": {"Amount": "1.25", "Unit": "USD"}}},
                        {"Keys": ["Amazon Simple Storage Service"], "Metrics": {"UnblendedCost": {"Amount": "0.75", "Unit": "USD"}}},
                    ],
                }
            ]
        return [
            {
                "TimePeriod": {"Start": "2026-04-01", "End": "2026-04-29"},
                "Total": {"UnblendedCost": {"Amount": "2.0", "Unit": "USD"}},
            }
        ]


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

    assert response["cost_summary"]["total_unblended_cost"] == 2.0
    assert response["cost_summary"]["month_to_date_unblended_cost"] == 2.0
    assert response["cost_summary"]["top_services"][0]["service"] == "Amazon Elastic Compute Cloud - Compute"
    assert response["finding_count"] == 1
    assert response["recommendation_count"] == 1
    assert response["findings"][0]["resource_id"] == "vol-001"
    assert response["recommendations"][0]["finding"]["resource_id"] == "vol-001"
    assert response["errors"] == [
        {
            "detector": "spend_spikes",
            "error_type": "RuntimeError",
            "message": "Cost Explorer is not enabled",
        }
    ]


def test_run_guardrail_returns_cost_summary_error_without_failing(monkeypatch) -> None:
    class FailingCostFactory(FakeFactory):
        def monthly_unblended_costs(self, **kwargs):
            raise RuntimeError("Cost Explorer data is unavailable")

    monkeypatch.setattr(app, "AwsClientFactory", FailingCostFactory)
    monkeypatch.setattr(app, "detect_idle_resources", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_spend_spikes", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(settings(), send_alerts=False)

    assert response["cost_summary"] is None
    assert response["errors"] == [
        {
            "detector": "cost_summary",
            "error_type": "RuntimeError",
            "message": "Cost Explorer data is unavailable",
        }
    ]


def test_run_guardrail_accepts_cost_months_filter(monkeypatch) -> None:
    class MultiMonthFactory(FakeFactory):
        def monthly_unblended_costs(self, **kwargs):
            assert kwargs["start"] < kwargs["end"]
            if kwargs.get("group_by_service"):
                return [
                    {
                        "TimePeriod": {"Start": "2026-03-01", "End": "2026-04-01"},
                        "Groups": [
                            {"Keys": ["AWS Lambda"], "Metrics": {"UnblendedCost": {"Amount": "3", "Unit": "USD"}}}
                        ],
                    }
                ]
            return [
                {
                    "TimePeriod": {"Start": "2026-03-01", "End": "2026-04-01"},
                    "Total": {"UnblendedCost": {"Amount": "3", "Unit": "USD"}},
                },
                {
                    "TimePeriod": {"Start": "2026-04-01", "End": "2026-04-29"},
                    "Total": {"UnblendedCost": {"Amount": "4", "Unit": "USD"}},
                },
            ]

    monkeypatch.setattr(app, "AwsClientFactory", MultiMonthFactory)
    monkeypatch.setattr(app, "detect_idle_resources", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_spend_spikes", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(settings(), send_alerts=False, cost_months=6)

    assert response["cost_summary"]["months"] == 6
    assert response["cost_summary"]["total_unblended_cost"] == 7
    assert response["cost_summary"]["month_to_date_unblended_cost"] == 4
    assert response["cost_summary"]["monthly_costs"][0]["amount"] == 3


def test_lambda_handler_returns_http_health_response(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", settings)

    response = app.lambda_handler(
        {
            "rawPath": "/health",
            "requestContext": {"http": {"method": "GET", "path": "/health"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert '"status": "ok"' in response["body"]


def test_lambda_handler_requires_google_token_when_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", lambda: replace(settings(), google_client_id="client.apps.googleusercontent.com"))

    response = app.lambda_handler(
        {
            "rawPath": "/health",
            "requestContext": {"http": {"method": "GET", "path": "/health"}},
        },
        None,
    )

    assert response["statusCode"] == 401
    assert "Missing Google sign-in token" in response["body"]


def test_lambda_handler_accepts_verified_google_user(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", lambda: replace(settings(), google_client_id="client.apps.googleusercontent.com"))
    monkeypatch.setattr(app, "verify_google_user", lambda loaded_settings, headers: {"email": "owner@example.com"})

    response = app.lambda_handler(
        {
            "rawPath": "/health",
            "headers": {"authorization": "Bearer token"},
            "requestContext": {"http": {"method": "GET", "path": "/health"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert '"authenticated_user": "owner@example.com"' in response["body"]


def test_lambda_handler_serves_swagger_docs() -> None:
    response = app.lambda_handler(
        {
            "rawPath": "/docs",
            "requestContext": {"http": {"method": "GET", "path": "/docs"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert response["headers"]["content-type"].startswith("text/html")
    assert "SwaggerUIBundle" in response["body"]


def test_lambda_handler_serves_swagger_docs_without_loading_settings(monkeypatch) -> None:
    def fail_load_settings():
        raise RuntimeError("config should not be loaded for docs")

    monkeypatch.setattr(app, "load_settings", fail_load_settings)

    response = app.lambda_handler(
        {
            "rawPath": "/docs",
            "requestContext": {"http": {"method": "GET", "path": "/docs"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert "SwaggerUIBundle" in response["body"]


def test_lambda_handler_serves_openapi_spec() -> None:
    response = app.lambda_handler(
        {
            "rawPath": "/openapi.json",
            "requestContext": {"http": {"method": "GET", "path": "/openapi.json"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert "Cloud Cost Guardrail Bot API" in response["body"]


def test_lambda_handler_returns_bad_request_for_invalid_http_body() -> None:
    response = app.lambda_handler(
        {
            "rawPath": "/run",
            "body": "{",
            "requestContext": {"http": {"method": "POST", "path": "/run"}},
        },
        None,
    )

    assert response["statusCode"] == 400


def test_lambda_handler_passes_cost_months_to_guardrail(monkeypatch) -> None:
    captured = {}

    def fake_run_guardrail(loaded_settings, *, send_alerts, cost_months):
        captured["cost_months"] = cost_months
        return {"cost_summary": {"months": cost_months}, "finding_count": 0, "recommendation_count": 0, "notifications": [], "errors": []}

    monkeypatch.setattr(app, "load_settings", settings)
    monkeypatch.setattr(app, "run_guardrail", fake_run_guardrail)

    response = app.lambda_handler(
        {
            "rawPath": "/run",
            "body": '{"send_alerts": false, "cost_months": 12}',
            "requestContext": {"http": {"method": "POST", "path": "/run"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert captured["cost_months"] == 12


def test_lambda_handler_cost_summary_endpoint_uses_months_query(monkeypatch) -> None:
    monkeypatch.setattr(app, "AwsClientFactory", FakeFactory)
    monkeypatch.setattr(app, "load_settings", settings)

    response = app.lambda_handler(
        {
            "rawPath": "/costs/summary",
            "queryStringParameters": {"months": "6"},
            "requestContext": {"http": {"method": "GET", "path": "/costs/summary"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert '"months": 6' in response["body"]
    assert '"total_unblended_cost": 2.0' in response["body"]


def test_lambda_handler_recommendations_endpoint_is_read_only(monkeypatch) -> None:
    captured = {}

    def fake_run_guardrail(loaded_settings, *, send_alerts, cost_months):
        captured["send_alerts"] = send_alerts
        captured["cost_months"] = cost_months
        return {
            "cost_summary": {"months": cost_months},
            "finding_count": 1,
            "recommendation_count": 1,
            "findings": [{"resource_id": "vol-001"}],
            "recommendations": [
                {
                    "action": "delete unattached volume",
                    "finding": {"category": "unattached_ebs", "resource_type": "ebs-volume", "resource_id": "vol-001"},
                }
            ],
            "notifications": [{"channel": "gmail", "delivered": True, "detail": "sent"}],
            "errors": [],
        }

    monkeypatch.setattr(app, "load_settings", settings)
    monkeypatch.setattr(app, "run_guardrail", fake_run_guardrail)

    response = app.lambda_handler(
        {
            "rawPath": "/recommendations",
            "queryStringParameters": {"months": "3"},
            "requestContext": {"http": {"method": "GET", "path": "/recommendations"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert captured == {"send_alerts": False, "cost_months": 3}
    body = json.loads(response["body"])
    assert body["type"] == "recommendations"
    assert body["findings"] == [{"resource_id": "vol-001"}]
    assert body["recommendations"][0]["action"] == "delete unattached volume"
    assert body["recommendations"][0]["status"] == "new"
    assert body["recommendations"][0]["recommendation_id"]
    assert "notifications" not in body


def test_lambda_handler_alerts_run_endpoint_always_sends_alerts(monkeypatch) -> None:
    captured = {}

    def fake_run_guardrail(loaded_settings, *, send_alerts, cost_months):
        captured["send_alerts"] = send_alerts
        captured["cost_months"] = cost_months
        return {
            "cost_summary": {"months": cost_months},
            "finding_count": 1,
            "recommendation_count": 1,
            "findings": [{"resource_id": "vol-001"}],
            "recommendations": [{"action": "delete unattached volume"}],
            "notifications": [{"channel": "gmail", "delivered": True, "detail": "sent"}],
            "errors": [],
        }

    monkeypatch.setattr(app, "load_settings", settings)
    monkeypatch.setattr(app, "run_guardrail", fake_run_guardrail)

    response = app.lambda_handler(
        {
            "rawPath": "/alerts/run",
            "body": '{"send_alerts": false, "cost_months": 12}',
            "requestContext": {"http": {"method": "POST", "path": "/alerts/run"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    assert captured == {"send_alerts": True, "cost_months": 12}
    body = json.loads(response["body"])
    assert body["type"] == "alert_run"
    assert body["alert_run"]["delivery_status"] == "delivered"
    assert body["alert_run"]["recommendations_sent_count"] == 1
    assert "findings" not in body
    assert "recommendations" not in body


def test_lambda_handler_rejects_invalid_month_filter(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", settings)

    response = app.lambda_handler(
        {
            "rawPath": "/recommendations",
            "queryStringParameters": {"months": "24"},
            "requestContext": {"http": {"method": "GET", "path": "/recommendations"}},
        },
        None,
    )

    assert response["statusCode"] == 400
    assert "between 1 and 12" in response["body"]


def test_lambda_handler_rejects_disallowed_gmail_recipient(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", settings)

    response = app.lambda_handler(
        {
            "rawPath": "/alerts/run",
            "body": '{"gmail_recipient": "attacker@example.com", "alert_channels": ["gmail"]}',
            "requestContext": {"http": {"method": "POST", "path": "/alerts/run"}},
        },
        None,
    )

    assert response["statusCode"] == 400
    assert "allowed alert recipients" in response["body"]


def test_lambda_handler_updates_recommendation_status(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", settings)
    monkeypatch.setattr(
        app,
        "update_status",
        lambda loaded_settings, recommendation_id, status: {
            "recommendation_id": recommendation_id,
            "status": status,
            "updated_at": "2026-04-29T00:00:00+00:00",
        },
    )

    response = app.lambda_handler(
        {
            "rawPath": "/recommendations/status",
            "body": '{"recommendation_id": "rec-001", "status": "acknowledged"}',
            "requestContext": {"http": {"method": "PATCH", "path": "/recommendations/status"}},
        },
        None,
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["recommendation_id"] == "rec-001"
    assert body["status"] == "acknowledged"


def test_lambda_handler_rejects_invalid_recommendation_status(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", settings)

    response = app.lambda_handler(
        {
            "rawPath": "/recommendations/status",
            "body": '{"recommendation_id": "rec-001", "status": "closed"}',
            "requestContext": {"http": {"method": "PATCH", "path": "/recommendations/status"}},
        },
        None,
    )

    assert response["statusCode"] == 400
    assert "status must be one of" in response["body"]
