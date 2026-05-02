from __future__ import annotations

from dataclasses import asdict
from dataclasses import replace
from datetime import date, timedelta
import json
import logging
from typing import Any

from auth import AuthError
from auth import verify_google_user
from aws_clients import AwsClientFactory
from billing_console import billing_console_federation_url
from config import Settings
from config import load_settings
from detectors.idle_resources import detect_idle_resources
from detectors.savings import detect_savings_opportunities
from detectors.spend_spikes import detect_spend_spikes
from models import Finding
from models import NotificationResult
from recommendations import build_recommendations
from recommendation_status import enrich_recommendations
from recommendation_status import update_status

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OPENAPI_SPEC: dict[str, Any] = {
    "openapi": "3.0.3",
    "info": {
        "title": "Cloud Cost Guardrail Bot API",
        "version": "0.1.0",
        "description": "HTTP API for cost summaries, recommendations, alerts, and health checks.",
    },
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "responses": {
                    "200": {
                        "description": "Current runtime and notification configuration status.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
        "/billing/console-url": {
            "get": {
                "summary": "Federated AWS Billing console URL",
                "description": "Uses STS AssumeRole and AWS federation to return a short-lived console sign-in URL to Billing.",
                "responses": {
                    "200": {
                        "description": "Sign-in URL for the AWS Billing console.",
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"url": {"type": "string"}}}}},
                    },
                    "502": {"description": "STS or federation failure."},
                    "503": {"description": "Feature not configured."},
                },
            }
        },
        "/costs/summary": {
            "get": {
                "summary": "Get cost summary",
                "parameters": [
                    {
                        "name": "months",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 1, "minimum": 1, "maximum": 12},
                        "description": "Number of months to include in the cost summary.",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Cost summary with monthly costs and top services.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
        "/recommendations": {
            "get": {
                "summary": "Get recommendations without sending alerts",
                "parameters": [
                    {
                        "name": "months",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 1, "minimum": 1, "maximum": 12},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Read-only cost summary, findings, recommendations, and detector errors.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
        "/recommendations/status": {
            "patch": {
                "summary": "Update recommendation workflow status",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["recommendation_id", "status"],
                                "properties": {
                                    "recommendation_id": {"type": "string"},
                                    "status": {
                                        "type": "string",
                                        "enum": ["new", "acknowledged", "in_progress", "resolved"],
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Updated recommendation status.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "400": {"description": "Invalid status update."},
                },
            }
        },
        "/alerts/run": {
            "post": {
                "summary": "Run checks and send configured alerts",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "gmail_recipient": {"type": "string", "format": "email"},
                                    "alert_channels": {
                                        "type": "array",
                                        "items": {"type": "string", "enum": ["gmail", "whatsapp"]},
                                    },
                                    "cost_months": {"type": "integer", "default": 1, "minimum": 1, "maximum": 12},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Alert delivery status, notification results, summary counts, cost summary, and detector errors.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "400": {"description": "Invalid request body."},
                },
            }
        },
        "/run": {
            "post": {
                "summary": "Deprecated compatibility endpoint for running guardrail checks",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "send_alerts": {"type": "boolean", "default": True},
                                    "gmail_recipient": {"type": "string", "format": "email"},
                                    "alert_channels": {
                                        "type": "array",
                                        "items": {"type": "string", "enum": ["gmail", "whatsapp"]},
                                    },
                                    "cost_months": {
                                        "type": "integer",
                                        "default": 1,
                                        "minimum": 1,
                                        "maximum": 12,
                                        "description": "Number of months to include in cost_summary.",
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Current month cost summary, guardrail findings, notification results, and detector errors.",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "400": {"description": "Invalid request body."},
                },
            }
        },
    },
}

SWAGGER_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Cloud Cost Guardrail Bot API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: "/openapi.json",
          dom_id: "#swagger-ui"
        });
      };
    </script>
  </body>
</html>
"""


def _notify(settings: Any, recommendations: Any) -> list[NotificationResult]:
    results: list[NotificationResult] = []
    if "gmail" in settings.alert_channels:
        try:
            from notifiers.gmail import send_gmail_alert

            results.append(send_gmail_alert(settings, recommendations))
        except Exception as exc:  # Lambda should report one channel failure without hiding all findings.
            logger.exception("Gmail notification failed")
            results.append(NotificationResult("gmail", False, str(exc)))
    if "whatsapp" in settings.alert_channels:
        try:
            from notifiers.whatsapp import send_whatsapp_alert

            results.append(send_whatsapp_alert(settings, recommendations))
        except Exception as exc:
            logger.exception("WhatsApp notification failed")
            results.append(NotificationResult("whatsapp", False, str(exc)))
    return results


def _serializable_dataclass(value: Any) -> dict[str, Any]:
    return asdict(value)


def _run_detector(name: str, detector: Any, factory: AwsClientFactory, settings: Settings) -> tuple[list[Finding], dict[str, str] | None]:
    try:
        return detector(factory, settings), None
    except Exception as exc:
        logger.exception("%s detector failed", name)
        return [], {"detector": name, "error_type": type(exc).__name__, "message": str(exc)}


def _add_months(month_start: date, months: int) -> date:
    month_index = month_start.month - 1 + months
    return date(month_start.year + month_index // 12, month_index % 12 + 1, 1)


def _cost_window(months: int) -> tuple[date, date]:
    today = date.today()
    current_month = today.replace(day=1)
    start = _add_months(current_month, -(months - 1))
    # Cost Explorer end date is exclusive. Tomorrow includes current partial month-to-date data.
    end = today + timedelta(days=1)
    return start, end


def _cost_amount(metric: dict[str, Any]) -> tuple[float, str]:
    return float(metric.get("Amount", 0.0)), str(metric.get("Unit", "USD"))


def _ce_preferred_amount(metrics: dict[str, Any]) -> tuple[float, str]:
    """Prefer UnblendedCost; fall back to NetUnblendedCost if unblended is absent."""
    for key in ("UnblendedCost", "NetUnblendedCost"):
        raw = metrics.get(key, {})
        if raw and raw.get("Amount") not in (None, ""):
            return _cost_amount(raw)
    return 0.0, "USD"


def _first_day_next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _sum_daily_mtd_costs(
    factory: AwsClientFactory,
    *,
    month_start: date,
    end_exclusive: date,
) -> tuple[float | None, str]:
    """Sum preferred CE metric (net unblended first) for [month_start, end_exclusive)."""
    if month_start >= end_exclusive:
        return 0.0, "USD"
    try:
        rows = factory.daily_unblended_costs(
            start=month_start.isoformat(),
            end=end_exclusive.isoformat(),
            group_by_service=False,
        )
    except Exception:
        logger.exception("daily cost sum for MTD failed")
        return None, "USD"
    total = 0.0
    currency = "USD"
    for row in rows:
        amt, currency = _ce_preferred_amount(row.get("Total", {}))
        total += amt
    return total, currency


def _cost_summary(
    factory: AwsClientFactory,
    *,
    months: int = 1,
    top_n: int = 10,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    start, end = _cost_window(months)
    try:
        monthly_results = factory.monthly_unblended_costs(
            start=start.isoformat(),
            end=end.isoformat(),
            group_by_service=False,
        )
        service_results = factory.monthly_unblended_costs(
            start=start.isoformat(),
            end=end.isoformat(),
            group_by_service=True,
        )
    except Exception as exc:
        logger.exception("cost_summary detector failed")
        return None, {"detector": "cost_summary", "error_type": type(exc).__name__, "message": str(exc)}

    monthly_costs: list[dict[str, Any]] = []
    total = 0.0
    currency = "USD"
    for result in monthly_results:
        amount, currency = _ce_preferred_amount(result.get("Total", {}))
        total += amount
        monthly_costs.append(
            {
                "start": result.get("TimePeriod", {}).get("Start"),
                "end": result.get("TimePeriod", {}).get("End"),
                "amount": round(amount, 4),
                "currency": currency,
            }
        )

    service_totals: dict[str, float] = {}
    for result in service_results:
        for group in result.get("Groups", []):
            service = group.get("Keys", ["Unknown"])[0]
            amount, currency = _ce_preferred_amount(group.get("Metrics", {}))
            service_totals[service] = service_totals.get(service, 0.0) + amount

    service_costs = [
        {"service": service, "amount": round(amount, 4), "currency": currency}
        for service, amount in sorted(service_totals.items(), key=lambda item: item[1], reverse=True)
        if amount > 0
    ]

    today = date.today()
    current_month_start = today.replace(day=1)
    current_key = current_month_start.isoformat()
    mtd_daily, mtd_currency = _sum_daily_mtd_costs(factory, month_start=current_month_start, end_exclusive=end)

    mtd_amount: float
    if mtd_daily is not None:
        mtd_amount = round(mtd_daily, 4)
        patched = False
        for row in monthly_costs:
            if row.get("start") == current_key:
                row["amount"] = mtd_amount
                row["currency"] = mtd_currency
                patched = True
                break
        if not patched and mtd_amount > 0:
            monthly_costs.append(
                {
                    "start": current_key,
                    "end": _first_day_next_month(current_month_start).isoformat(),
                    "amount": mtd_amount,
                    "currency": mtd_currency,
                }
            )
            monthly_costs.sort(key=lambda r: r.get("start") or "")
        total = round(sum(row["amount"] for row in monthly_costs), 4)
    else:
        mtd_amount = round(monthly_costs[-1]["amount"], 4) if monthly_costs else 0.0

    return (
        {
            "months": months,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "total_unblended_cost": round(total, 4),
            "month_to_date_unblended_cost": mtd_amount,
            "currency": currency,
            "monthly_costs": monthly_costs,
            "top_services": service_costs[:top_n],
            "usage_cost_basis": "unblended_preferred",
        },
        None,
    )


def run_guardrail(settings: Settings | None = None, *, send_alerts: bool = True, cost_months: int = 1) -> dict[str, Any]:
    settings = settings or load_settings()
    factory = AwsClientFactory(settings.aws_region)

    findings: list[Finding] = []
    errors: list[dict[str, str]] = []
    normalized_cost_months = max(1, min(cost_months, 12))
    cost_summary, cost_error = _cost_summary(factory, months=normalized_cost_months)
    if cost_error:
        errors.append(cost_error)

    detectors = [
        ("idle_resources", detect_idle_resources),
        ("spend_spikes", detect_spend_spikes),
        ("savings_opportunities", detect_savings_opportunities),
    ]
    for name, detector in detectors:
        detector_findings, error = _run_detector(name, detector, factory, settings)
        findings.extend(detector_findings)
        if error:
            errors.append(error)

    recommendations = build_recommendations(findings)
    notification_results = _notify(settings, recommendations) if send_alerts and recommendations else []

    response = {
        "cost_summary": cost_summary,
        "finding_count": len(findings),
        "recommendation_count": len(recommendations),
        "findings": [_serializable_dataclass(finding) for finding in findings],
        "recommendations": [_serializable_dataclass(recommendation) for recommendation in recommendations],
        "notifications": [result.__dict__ for result in notification_results],
        "errors": errors,
    }
    logger.info("Cloud Cost Guardrail completed: %s", json.dumps(response))
    return response


def _json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


def _html_response(status_code: int, body: str) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "text/html; charset=utf-8"},
        "body": body,
    }


def _is_http_api_event(event: dict[str, Any] | None) -> bool:
    if not isinstance(event, dict):
        return False
    request_context = event.get("requestContext")
    return bool(isinstance(request_context, dict) and "http" in request_context)


def _http_method_and_path(event: dict[str, Any]) -> tuple[str, str]:
    http = event.get("requestContext", {}).get("http", {})
    return str(http.get("method", "")).upper(), str(event.get("rawPath") or http.get("path") or "/")


def _json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw_body = event.get("body")
    if not raw_body:
        return {}
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object")
    return parsed


def _query_params(event: dict[str, Any]) -> dict[str, str]:
    raw_params = event.get("queryStringParameters") or {}
    if not isinstance(raw_params, dict):
        return {}
    return {str(key): str(value) for key, value in raw_params.items() if value is not None}


def _headers(event: dict[str, Any]) -> dict[str, str]:
    raw_headers = event.get("headers") or {}
    if not isinstance(raw_headers, dict):
        return {}
    return {str(key).lower(): str(value) for key, value in raw_headers.items() if value is not None}


def _cost_months_from_value(raw_value: Any, default: int = 1) -> int:
    if raw_value is None or raw_value == "":
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("cost_months/months must be an integer") from exc
    if value < 1 or value > 12:
        raise ValueError("cost_months/months must be between 1 and 12")
    return value


def _apply_request_overrides(settings: Settings, body: dict[str, Any]) -> Settings:
    if body.get("gmail_recipient"):
        requested_recipient = str(body["gmail_recipient"]).strip().lower()
        allowed_recipients = {recipient.strip().lower() for recipient in settings.allowed_alert_recipients if recipient.strip()}
        if requested_recipient not in allowed_recipients:
            raise ValueError("gmail_recipient is not in the allowed alert recipients list")
        settings = replace(settings, gmail_recipient=str(body["gmail_recipient"]).strip())
    if body.get("alert_channels"):
        settings = replace(settings, alert_channels=tuple(str(channel).lower() for channel in body["alert_channels"]))
    return settings


def _recommendation_response(settings: Settings, *, cost_months: int, send_alerts: bool) -> dict[str, Any]:
    result = run_guardrail(settings, send_alerts=send_alerts, cost_months=cost_months)
    recommendations = enrich_recommendations(settings, result["recommendations"])
    return {
        "type": "recommendations",
        "cost_summary": result["cost_summary"],
        "finding_count": result["finding_count"],
        "recommendation_count": len(recommendations),
        "findings": result["findings"],
        "recommendations": recommendations,
        "errors": result["errors"],
    }


def _alert_run_response(settings: Settings, *, cost_months: int) -> dict[str, Any]:
    result = run_guardrail(settings, send_alerts=True, cost_months=cost_months)
    notifications = result["notifications"]
    recommendation_count = result["recommendation_count"]
    if recommendation_count == 0:
        delivery_status = "skipped_no_recommendations"
    elif not notifications:
        delivery_status = "skipped_no_channels"
    elif all(notification.get("delivered") for notification in notifications):
        delivery_status = "delivered"
    else:
        delivery_status = "partial_or_failed"

    return {
        "type": "alert_run",
        "alert_run": {
            "delivery_status": delivery_status,
            "requested_channels": list(settings.alert_channels),
            "notification_count": len(notifications),
            "recommendations_sent_count": recommendation_count if notifications else 0,
        },
        "cost_summary": result["cost_summary"],
        "finding_count": result["finding_count"],
        "recommendation_count": recommendation_count,
        "notifications": notifications,
        "errors": result["errors"],
    }


def _handle_http_api_event(event: dict[str, Any]) -> dict[str, Any]:
    method, path = _http_method_and_path(event)

    if method == "GET" and path == "/docs":
        return _html_response(200, SWAGGER_UI_HTML)

    if method == "GET" and path == "/openapi.json":
        return _json_response(200, OPENAPI_SPEC)

    settings = load_settings()

    try:
        user = verify_google_user(settings, _headers(event))
    except AuthError as exc:
        return _json_response(exc.status_code, {"error": str(exc)})

    if method == "GET" and path == "/health":
        return _json_response(
            200,
            {
                "status": "ok",
                "auth_enabled": bool(settings.google_client_id),
                "authenticated_user": user.get("email") if user else None,
                "target_region": settings.aws_region,
                "alert_channels": settings.alert_channels,
                "gmail_token_configured": settings.gmail_token_json is not None,
                "gmail_recipient_configured": bool(settings.gmail_recipient),
                "whatsapp_configured": bool(
                    settings.whatsapp_access_token and settings.whatsapp_phone_number_id and settings.whatsapp_to
                ),
                "billing_console_federation_enabled": bool(settings.billing_console_role_arn),
            },
        )

    if method == "GET" and path == "/billing/console-url":
        try:
            url = billing_console_federation_url(settings, user)
        except ValueError as exc:
            return _json_response(503, {"error": str(exc)})
        except RuntimeError as exc:
            return _json_response(502, {"error": str(exc)})
        return _json_response(200, {"url": url})

    if method == "GET" and path == "/costs/summary":
        try:
            months = _cost_months_from_value(_query_params(event).get("months"))
        except ValueError as exc:
            return _json_response(400, {"error": str(exc)})
        factory = AwsClientFactory(settings.aws_region)
        cost_summary, cost_error = _cost_summary(factory, months=months)
        return _json_response(200, {"cost_summary": cost_summary, "errors": [cost_error] if cost_error else []})

    if method == "GET" and path == "/recommendations":
        try:
            months = _cost_months_from_value(_query_params(event).get("months"))
        except ValueError as exc:
            return _json_response(400, {"error": str(exc)})
        return _json_response(200, _recommendation_response(settings, cost_months=months, send_alerts=False))

    if method == "PATCH" and path == "/recommendations/status":
        try:
            body = _json_body(event)
            updated = update_status(settings, str(body.get("recommendation_id", "")), str(body.get("status", "")))
        except ValueError as exc:
            return _json_response(400, {"error": str(exc)})
        except RuntimeError as exc:
            return _json_response(503, {"error": str(exc)})
        return _json_response(200, updated)

    if method == "POST" and path in {"/alerts/run", "/run"}:
        try:
            body = _json_body(event)
        except ValueError as exc:
            return _json_response(400, {"error": str(exc)})

        try:
            settings = _apply_request_overrides(settings, body)
        except ValueError as exc:
            return _json_response(400, {"error": str(exc)})
        try:
            cost_months = _cost_months_from_value(body.get("cost_months"))
        except ValueError as exc:
            return _json_response(400, {"error": str(exc)})
        if path == "/alerts/run":
            return _json_response(200, _alert_run_response(settings, cost_months=cost_months))
        send_alerts = bool(body.get("send_alerts", True))
        return _json_response(200, run_guardrail(settings, send_alerts=send_alerts, cost_months=cost_months))

    return _json_response(404, {"error": f"No route for {method} {path}"})


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    if _is_http_api_event(event):
        return _handle_http_api_event(event)
    return run_guardrail(load_settings(), send_alerts=True)


if __name__ == "__main__":
    print(json.dumps(run_guardrail(), indent=2))
