from __future__ import annotations

from dataclasses import asdict
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
import logging
from typing import Any

from auth import AuthError
from auth import verify_google_user
from aws_clients import AwsClientFactory, ce_amount_from_keys, ce_preferred_amount, ce_row_metric_map
from billing_console import billing_console_federation_url
from config import Settings
from config import load_settings
from detectors.idle_resources import detect_idle_resources
from detectors.savings import detect_savings_opportunities
from detectors.spend_spikes import detect_spend_spikes
from invoice_billing import fetch_invoice_billing
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


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _cost_window(months: int) -> tuple[date, date]:
    today = _utc_today()
    current_month = today.replace(day=1)
    start = _add_months(current_month, -(months - 1))
    # Cost Explorer end date is exclusive. Tomorrow includes current partial month-to-date data.
    end = today + timedelta(days=1)
    return start, end


def _first_day_next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


# Ungrouped CE totals can be 0 while grouped-by-SERVICE still has small amounts (API quirk for tiny spend).
_CE_ZEROISH = 1e-9
# Daily MTD "invoice-style" hint: amortization-heavy metrics (not the same as the AWS invoice PDF).
_CE_INVOICE_HINT_METRICS: tuple[str, ...] = ("NetAmortizedCost", "AmortizedCost")


def _fin_cost(x: float) -> float:
    """Round and drop negative zero for JSON-friendly numbers."""
    r = float(round(x + 0.0, 4))
    return 0.0 + r


def _period_start_key(value: object) -> str | None:
    """Normalize CE TimePeriod.Start to YYYY-MM-DD for dict keys and comparisons (boto3 may use date objects)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s or None


def _aggregate_grouped_monthly(
    service_results: list[dict[str, Any]],
) -> tuple[dict[str, float], dict[str, str], dict[str, float], dict[str, str]]:
    """Per calendar month sums from grouped results, per-service totals, and last-seen currency per service."""
    monthly_sum: dict[str, float] = {}
    monthly_currency: dict[str, str] = {}
    service_totals: dict[str, float] = {}
    service_currency: dict[str, str] = {}
    for result in service_results:
        mstart = result.get("TimePeriod", {}).get("Start")
        nk = _period_start_key(mstart)
        if not nk:
            continue
        month_sum = 0.0
        month_currency = "USD"
        for group in result.get("Groups", []):
            keys = group.get("Keys", ["Unknown"])
            service = keys[0] if keys else "Unknown"
            amount, cur = ce_preferred_amount(group.get("Metrics", {}))
            month_sum += amount
            month_currency = cur
            service_totals[service] = service_totals.get(service, 0.0) + amount
            service_currency[service] = cur
        monthly_sum[nk] = monthly_sum.get(nk, 0.0) + month_sum
        monthly_currency[nk] = month_currency
    return monthly_sum, monthly_currency, service_totals, service_currency


def _grouped_sum_for_calendar_month(
    monthly_grouped_sum: dict[str, float],
    monthly_group_currency: dict[str, str],
    *,
    current_key: str,
    month_start: date,
) -> tuple[float | None, str | None]:
    """Resolve grouped-by-SERVICE month total; fall back to any CE key in the same calendar month (key drift)."""
    v = monthly_grouped_sum.get(current_key)
    if v is not None and abs(v) >= _CE_ZEROISH:
        return v, monthly_group_currency.get(current_key)
    prefix = f"{month_start.year:04d}-{month_start.month:02d}-"
    acc = 0.0
    cur: str | None = monthly_group_currency.get(current_key)
    for k, g in monthly_grouped_sum.items():
        if not k:
            continue
        if str(k).startswith(prefix) and abs(g) >= _CE_ZEROISH:
            acc += g
            cur = monthly_group_currency.get(k, cur)
    if abs(acc) >= _CE_ZEROISH:
        return acc, cur
    if v is not None:
        return v, monthly_group_currency.get(current_key)
    return None, None


def _month_row_matches(
    row_start: object,
    *,
    current_key: str,
    month_start: date,
) -> bool:
    rs = _period_start_key(row_start) or row_start
    if not rs:
        return False
    s = str(rs)
    if s == current_key:
        return True
    prefix = f"{month_start.year:04d}-{month_start.month:02d}-"
    return s.startswith(prefix)


def _sum_daily_mtd_and_invoice_hint(
    factory: AwsClientFactory,
    *,
    month_start: date,
    end_exclusive: date,
) -> tuple[float | None, str, float | None, str]:
    """Sum usage-preferred and amortized-style CE metrics for [month_start, end_exclusive) (daily rows).

    Returns (usage_mtd, usage_ccy, invoice_hint_mtd, invoice_ccy). On CE failure, usage and hint are None.
    """
    if month_start >= end_exclusive:
        return 0.0, "USD", 0.0, "USD"
    try:
        rows = factory.daily_unblended_costs(
            start=month_start.isoformat(),
            end=end_exclusive.isoformat(),
            group_by_service=False,
        )
    except Exception:
        logger.exception("daily cost sum for MTD failed")
        return None, "USD", None, "USD"
    total = 0.0
    currency = "USD"
    inv_total = 0.0
    inv_currency = "USD"
    for row in rows:
        m = ce_row_metric_map(row)
        amt, currency = ce_preferred_amount(m)
        total += amt
        i_amt, inv_currency = ce_amount_from_keys(m, _CE_INVOICE_HINT_METRICS)
        inv_total += i_amt
    return total, currency, inv_total, inv_currency


def _cost_summary(
    factory: AwsClientFactory,
    *,
    months: int = 1,
    top_n: int = 10,
    invoice_summary_enabled: bool = True,
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
        amount, currency = ce_preferred_amount(ce_row_metric_map(result))
        total += amount
        raw_start = result.get("TimePeriod", {}).get("Start")
        raw_end = result.get("TimePeriod", {}).get("End")
        start_key = _period_start_key(raw_start) or (str(raw_start) if raw_start is not None else None)
        end_key = _period_start_key(raw_end) or (str(raw_end) if raw_end is not None else None)
        monthly_costs.append(
            {
                "start": start_key,
                "end": end_key,
                "amount": _fin_cost(amount),
                "currency": currency,
            }
        )

    monthly_grouped_sum, monthly_group_currency, service_totals, service_currency = _aggregate_grouped_monthly(
        service_results
    )

    today = _utc_today()
    current_month_start = today.replace(day=1)
    current_key = _period_start_key(current_month_start.isoformat()) or current_month_start.isoformat()

    for row in monthly_costs:
        mstart = row.get("start")
        nk = _period_start_key(mstart) or mstart
        if not nk:
            continue
        gsum = monthly_grouped_sum.get(nk)
        if gsum is None:
            continue
        if abs(float(row["amount"])) < _CE_ZEROISH and abs(gsum) >= _CE_ZEROISH:
            row["amount"] = _fin_cost(gsum)
            row["currency"] = monthly_group_currency.get(nk, row.get("currency", "USD"))

    service_costs = [
        {"service": service, "amount": _fin_cost(amount), "currency": service_currency.get(service, "USD")}
        for service, amount in sorted(service_totals.items(), key=lambda item: item[1], reverse=True)
        if amount > _CE_ZEROISH
    ]

    mtd_daily, mtd_currency, mtd_invoice_hint, mtd_invoice_currency = _sum_daily_mtd_and_invoice_hint(
        factory, month_start=current_month_start, end_exclusive=end
    )
    grouped_current, grouped_current_currency = _grouped_sum_for_calendar_month(
        monthly_grouped_sum,
        monthly_group_currency,
        current_key=current_key,
        month_start=current_month_start,
    )

    mtd_amount: float
    if mtd_daily is not None:
        if abs(mtd_daily) < _CE_ZEROISH and grouped_current is not None and abs(grouped_current) >= _CE_ZEROISH:
            mtd_amount = _fin_cost(grouped_current)
            mtd_currency = grouped_current_currency or monthly_group_currency.get(current_key, mtd_currency)
        else:
            mtd_amount = _fin_cost(mtd_daily)
        patched = False
        for row in monthly_costs:
            if _month_row_matches(row.get("start"), current_key=current_key, month_start=current_month_start):
                row["amount"] = mtd_amount
                row["currency"] = mtd_currency
                patched = True
                break
        if not patched and abs(mtd_amount) >= _CE_ZEROISH:
            monthly_costs.append(
                {
                    "start": current_key,
                    "end": _first_day_next_month(current_month_start).isoformat(),
                    "amount": mtd_amount,
                    "currency": mtd_currency,
                }
            )
            monthly_costs.sort(key=lambda r: r.get("start") or "")
    else:
        mtd_amount = _fin_cost(float(monthly_costs[-1]["amount"])) if monthly_costs else 0.0

    total = _fin_cost(sum(float(row["amount"]) for row in monthly_costs)) if monthly_costs else 0.0

    for row in monthly_costs:
        if _month_row_matches(row.get("start"), current_key=current_key, month_start=current_month_start):
            currency = str(row.get("currency") or currency)
            break
    else:
        if monthly_costs:
            currency = str(monthly_costs[-1].get("currency") or currency)

    svc_sum = _fin_cost(sum(service_totals.values()))
    if abs(total) < _CE_ZEROISH and svc_sum > _CE_ZEROISH:
        total = svc_sum
        if abs(mtd_amount) < _CE_ZEROISH:
            mtd_amount = svc_sum
        if len(monthly_costs) == 1:
            monthly_costs[0]["amount"] = svc_sum
            monthly_costs[0]["currency"] = next(
                (monthly_group_currency[k] for k in sorted(monthly_group_currency) if k),
                currency,
            )
        else:
            for row in monthly_costs:
                if _month_row_matches(row.get("start"), current_key=current_key, month_start=current_month_start):
                    row["amount"] = mtd_amount
                    row["currency"] = mtd_currency
                    break

    total = _fin_cost(total)
    mtd_amount = _fin_cost(mtd_amount)

    if mtd_daily is not None and mtd_invoice_hint is not None:
        invoice_hint = _fin_cost(mtd_invoice_hint)
        invoice_ccy = mtd_invoice_currency
        invoice_basis = "ce_net_amortized_then_amortized_daily"
    else:
        invoice_hint = None
        invoice_ccy = None
        invoice_basis = None

    invoice_block = fetch_invoice_billing(factory, today, enabled=invoice_summary_enabled)

    return (
        {
            "months": months,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "total_unblended_cost": total,
            "month_to_date_unblended_cost": mtd_amount,
            "currency": currency,
            "monthly_costs": monthly_costs,
            "top_services": service_costs[:top_n],
            "usage_cost_basis": "ce_preferred_metrics",
            "month_to_date_invoice_hint": invoice_hint,
            "month_to_date_invoice_hint_currency": invoice_ccy,
            "invoice_hint_basis": invoice_basis,
            "invoice_billing": invoice_block,
        },
        None,
    )


def run_guardrail(settings: Settings | None = None, *, send_alerts: bool = True, cost_months: int = 1) -> dict[str, Any]:
    settings = settings or load_settings()
    factory = AwsClientFactory(settings.aws_region)

    findings: list[Finding] = []
    errors: list[dict[str, str]] = []
    normalized_cost_months = max(1, min(cost_months, 12))
    cost_summary, cost_error = _cost_summary(
        factory,
        months=normalized_cost_months,
        invoice_summary_enabled=settings.invoice_summary_enabled,
    )
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
        cost_summary, cost_error = _cost_summary(
            factory,
            months=months,
            invoice_summary_enabled=settings.invoice_summary_enabled,
        )
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
