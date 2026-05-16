from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from typing import Any

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
        billing_console_role_arn=None,
    )


def test_grouped_sum_for_calendar_month_prefix_fallback() -> None:
    """When exact current_key misses grouped dict, sum any CE keys in the same YYYY-MM."""
    ms = {"2026-05-01": 0.0003}
    mc = {"2026-05-01": "USD"}
    v, c = app._grouped_sum_for_calendar_month(ms, mc, current_key="2026-05-02", month_start=date(2026, 5, 1))
    assert v == 0.0003
    assert c == "USD"


class FakeFactory:
    def __init__(self, region_name: str) -> None:
        self.region_name = region_name

    def aws_account_id(self) -> str:
        return "123456789012"

    def list_invoice_summaries_for_billing_period(
        self, *, account_id: str, year: int, month: int
    ) -> list[dict[str, Any]]:
        return []

    def monthly_unblended_costs(self, **kwargs):
        cm = date.today().replace(day=1)
        nxt = app._first_day_next_month(cm)
        if kwargs.get("group_by_service"):
            return [
                {
                    "TimePeriod": {"Start": cm.isoformat(), "End": nxt.isoformat()},
                    "Groups": [
                        {
                            "Keys": ["Amazon Elastic Compute Cloud - Compute"],
                            "Metrics": {
                                "NetUnblendedCost": {"Amount": "1.25", "Unit": "USD"},
                                "UnblendedCost": {"Amount": "1.25", "Unit": "USD"},
                            },
                        },
                        {
                            "Keys": ["Amazon Simple Storage Service"],
                            "Metrics": {
                                "NetUnblendedCost": {"Amount": "0.75", "Unit": "USD"},
                                "UnblendedCost": {"Amount": "0.75", "Unit": "USD"},
                            },
                        },
                    ],
                }
            ]
        return [
            {
                "TimePeriod": {"Start": cm.isoformat(), "End": nxt.isoformat()},
                "Total": {
                    "NetUnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                    "UnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                },
            }
        ]

    def daily_unblended_costs(self, **kwargs):
        return [
            {
                "TimePeriod": {"Start": kwargs["start"], "End": kwargs["end"]},
                "Total": {
                    "NetUnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                    "UnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                    "NetAmortizedCost": {"Amount": "2.1", "Unit": "USD"},
                },
            }
        ]


def test_cost_summary_uses_grouped_monthly_when_ungrouped_and_daily_are_zero(monkeypatch) -> None:
    """CE often returns 0 on ungrouped Total/daily while grouped-by-SERVICE still has tiny line items."""

    class TinySpendFactory(FakeFactory):
        def monthly_unblended_costs(self, **kwargs):
            cm = date.today().replace(day=1)
            nxt = app._first_day_next_month(cm)
            if kwargs.get("group_by_service"):
                return [
                    {
                        "TimePeriod": {"Start": cm.isoformat(), "End": nxt.isoformat()},
                        "Groups": [
                            {
                                "Keys": ["AWS Lambda"],
                                "Metrics": {"UnblendedCost": {"Amount": "0.0001", "Unit": "USD"}},
                            },
                        ],
                    }
                ]
            return [
                {
                    "TimePeriod": {"Start": cm.isoformat(), "End": nxt.isoformat()},
                    "Total": {
                        "UnblendedCost": {"Amount": "0", "Unit": "USD"},
                        "BlendedCost": {"Amount": "0", "Unit": "USD"},
                    },
                }
            ]

        def daily_unblended_costs(self, **kwargs):
            return [
                {
                    "TimePeriod": {"Start": kwargs["start"], "End": kwargs["end"]},
                    "Total": {"UnblendedCost": {"Amount": "0", "Unit": "USD"}},
                }
            ]

    monkeypatch.setattr(app, "AwsClientFactory", TinySpendFactory)
    monkeypatch.setattr(app, "detect_idle_resources", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_spend_spikes", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(settings(), send_alerts=False, cost_months=1)

    assert response["cost_summary"]["month_to_date_unblended_cost"] == 0.0001
    assert response["cost_summary"]["month_to_date_invoice_hint"] == 0.0
    assert response["cost_summary"]["total_unblended_cost"] == 0.0001
    assert response["cost_summary"]["monthly_costs"][0]["amount"] == 0.0001


def test_cost_summary_matches_grouped_when_timeperiod_uses_date_objects(monkeypatch) -> None:
    """Boto3 may deserialize TimePeriod.Start as datetime.date; keys must still align with monthly rows."""

    class DatePeriodFactory(FakeFactory):
        def monthly_unblended_costs(self, **kwargs):
            cm = date(2026, 5, 1)
            nxt = date(2026, 6, 1)
            if kwargs.get("group_by_service"):
                return [
                    {
                        "TimePeriod": {"Start": cm, "End": nxt},
                        "Groups": [
                            {
                                "Keys": ["AWS Lambda"],
                                "Metrics": {"UnblendedCost": {"Amount": "0.0002", "Unit": "USD"}},
                            },
                        ],
                    }
                ]
            return [
                {
                    "TimePeriod": {"Start": cm, "End": nxt},
                    "Total": {"UnblendedCost": {"Amount": "0", "Unit": "USD"}},
                }
            ]

        def daily_unblended_costs(self, **kwargs):
            return [
                {
                    "TimePeriod": {"Start": kwargs["start"], "End": kwargs["end"]},
                    "Total": {
                        "UnblendedCost": {"Amount": "0.0002", "Unit": "USD"},
                        "NetAmortizedCost": {"Amount": "0.0005", "Unit": "USD"},
                    },
                }
            ]

    monkeypatch.setattr(app, "_utc_today", lambda: date(2026, 5, 10))
    monkeypatch.setattr(app, "AwsClientFactory", DatePeriodFactory)
    monkeypatch.setattr(app, "detect_idle_resources", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_spend_spikes", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(settings(), send_alerts=False, cost_months=1)

    assert response["cost_summary"]["month_to_date_unblended_cost"] == 0.0002
    assert response["cost_summary"]["month_to_date_invoice_hint"] == 0.0005
    assert response["cost_summary"]["total_unblended_cost"] == 0.0002


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
    assert response["cost_summary"]["month_to_date_invoice_hint"] == 2.1
    assert response["cost_summary"]["invoice_hint_basis"] == "ce_net_amortized_then_amortized_daily"
    assert response["cost_summary"]["invoice_billing"]["available"] is True
    assert response["cost_summary"]["invoice_billing"]["account_id"] == "123456789012"
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
                            {
                                "Keys": ["AWS Lambda"],
                                "Metrics": {
                                    "NetUnblendedCost": {"Amount": "3", "Unit": "USD"},
                                    "UnblendedCost": {"Amount": "3", "Unit": "USD"},
                                },
                            }
                        ],
                    }
                ]
            return [
                {
                    "TimePeriod": {"Start": "2026-03-01", "End": "2026-04-01"},
                    "Total": {
                        "NetUnblendedCost": {"Amount": "3", "Unit": "USD"},
                        "UnblendedCost": {"Amount": "3", "Unit": "USD"},
                    },
                },
                {
                    "TimePeriod": {"Start": "2026-04-01", "End": "2026-04-29"},
                    "Total": {
                        "NetUnblendedCost": {"Amount": "4", "Unit": "USD"},
                        "UnblendedCost": {"Amount": "4", "Unit": "USD"},
                    },
                },
            ]

        def daily_unblended_costs(self, **kwargs):
            return [
                {
                    "TimePeriod": {"Start": kwargs["start"], "End": kwargs["end"]},
                    "Total": {
                        "NetUnblendedCost": {"Amount": "4", "Unit": "USD"},
                        "UnblendedCost": {"Amount": "4", "Unit": "USD"},
                        "NetAmortizedCost": {"Amount": "5", "Unit": "USD"},
                    },
                }
            ]

    monkeypatch.setattr(app, "_utc_today", lambda: date(2026, 4, 15))
    monkeypatch.setattr(app, "AwsClientFactory", MultiMonthFactory)
    monkeypatch.setattr(app, "detect_idle_resources", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_spend_spikes", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(settings(), send_alerts=False, cost_months=6)

    assert response["cost_summary"]["months"] == 6
    assert response["cost_summary"]["total_unblended_cost"] == 7
    assert response["cost_summary"]["month_to_date_unblended_cost"] == 4
    assert response["cost_summary"]["month_to_date_invoice_hint"] == 5
    assert response["cost_summary"]["monthly_costs"][0]["amount"] == 3


def test_cost_summary_invoice_billing_prior_closed_invoice(monkeypatch) -> None:
    """AWS Invoice Summary API returns authoritative totals for closed billing months."""

    class InvoiceFactory(FakeFactory):
        def monthly_unblended_costs(self, **kwargs):
            cm = date(2026, 5, 1)
            nxt = date(2026, 6, 1)
            if kwargs.get("group_by_service"):
                return [
                    {
                        "TimePeriod": {"Start": cm.isoformat(), "End": nxt.isoformat()},
                        "Groups": [
                            {
                                "Keys": ["Amazon Elastic Compute Cloud - Compute"],
                                "Metrics": {
                                    "NetUnblendedCost": {"Amount": "1.25", "Unit": "USD"},
                                    "UnblendedCost": {"Amount": "1.25", "Unit": "USD"},
                                },
                            },
                        ],
                    }
                ]
            return [
                {
                    "TimePeriod": {"Start": cm.isoformat(), "End": nxt.isoformat()},
                    "Total": {
                        "NetUnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                        "UnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                        "NetAmortizedCost": {"Amount": "2.1", "Unit": "USD"},
                    },
                }
            ]

        def daily_unblended_costs(self, **kwargs):
            return [
                {
                    "TimePeriod": {"Start": kwargs["start"], "End": kwargs["end"]},
                    "Total": {
                        "NetUnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                        "UnblendedCost": {"Amount": "2.0", "Unit": "USD"},
                        "NetAmortizedCost": {"Amount": "2.1", "Unit": "USD"},
                    },
                }
            ]

        def list_invoice_summaries_for_billing_period(self, *, account_id: str, year: int, month: int):
            if year == 2026 and month == 4:
                return [
                    {
                        "InvoiceId": "inv-prior",
                        "BillingPeriod": {"Year": 2026, "Month": 4},
                        "IssuedDate": 1715000000000,
                        "BaseCurrencyAmount": {
                            "TotalAmount": "199.5",
                            "TotalAmountBeforeTax": "180.0",
                            "CurrencyCode": "USD",
                        },
                    }
                ]
            return []

    monkeypatch.setattr(app, "_utc_today", lambda: date(2026, 5, 10))
    monkeypatch.setattr(app, "AwsClientFactory", InvoiceFactory)
    monkeypatch.setattr(app, "detect_idle_resources", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_spend_spikes", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(settings(), send_alerts=False, cost_months=1)
    ib = response["cost_summary"]["invoice_billing"]
    assert ib["available"] is True
    assert ib["account_id"] == "123456789012"
    assert ib["prior_period"]["total_amount"] == 199.5
    assert ib["prior_period"]["total_before_tax"] == 180.0
    assert ib["prior_period"]["currency"] == "USD"
    assert ib["current_period"] is None


def test_cost_summary_skips_invoice_api_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(app, "AwsClientFactory", FakeFactory)
    monkeypatch.setattr(app, "detect_idle_resources", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_spend_spikes", lambda factory, loaded_settings: [])
    monkeypatch.setattr(app, "detect_savings_opportunities", lambda factory, loaded_settings: [])

    response = app.run_guardrail(replace(settings(), invoice_summary_enabled=False), send_alerts=False, cost_months=1)
    assert response["cost_summary"]["invoice_billing"] == {"available": False, "skipped": True}


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


def test_lambda_handler_billing_console_url_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(app, "load_settings", settings)
    monkeypatch.setattr(app, "verify_google_user", lambda loaded_settings, headers: {"email": "owner@example.com"})

    response = app.lambda_handler(
        {
            "rawPath": "/billing/console-url",
            "headers": {"authorization": "Bearer token"},
            "requestContext": {"http": {"method": "GET", "path": "/billing/console-url"}},
        },
        None,
    )

    assert response["statusCode"] == 503
    assert "not configured" in response["body"]


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
    body = json.loads(response["body"])
    assert body["cost_summary"]["month_to_date_invoice_hint"] == 2.1


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
