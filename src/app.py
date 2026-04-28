from __future__ import annotations

from dataclasses import replace
import json
import logging
from typing import Any

from aws_clients import AwsClientFactory
from config import Settings
from config import load_settings
from detectors.idle_resources import detect_idle_resources
from detectors.savings import detect_savings_opportunities
from detectors.spend_spikes import detect_spend_spikes
from models import Finding
from models import NotificationResult
from recommendations import build_recommendations

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OPENAPI_SPEC: dict[str, Any] = {
    "openapi": "3.0.3",
    "info": {
        "title": "Cloud Cost Guardrail Bot API",
        "version": "0.1.0",
        "description": "HTTP API for health checks and on-demand AWS cost guardrail runs.",
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
        "/run": {
            "post": {
                "summary": "Run guardrail checks",
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
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Guardrail findings, notification results, and detector errors.",
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


def _run_detector(name: str, detector: Any, factory: AwsClientFactory, settings: Settings) -> tuple[list[Finding], dict[str, str] | None]:
    try:
        return detector(factory, settings), None
    except Exception as exc:
        logger.exception("%s detector failed", name)
        return [], {"detector": name, "error_type": type(exc).__name__, "message": str(exc)}


def run_guardrail(settings: Settings | None = None, *, send_alerts: bool = True) -> dict[str, Any]:
    settings = settings or load_settings()
    factory = AwsClientFactory(settings.aws_region)

    findings: list[Finding] = []
    errors: list[dict[str, str]] = []
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
        "finding_count": len(findings),
        "recommendation_count": len(recommendations),
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


def _handle_http_api_event(event: dict[str, Any]) -> dict[str, Any]:
    method, path = _http_method_and_path(event)

    if method == "GET" and path == "/docs":
        return _html_response(200, SWAGGER_UI_HTML)

    if method == "GET" and path == "/openapi.json":
        return _json_response(200, OPENAPI_SPEC)

    settings = load_settings()

    if method == "GET" and path == "/health":
        return _json_response(
            200,
            {
                "status": "ok",
                "target_region": settings.aws_region,
                "alert_channels": settings.alert_channels,
                "gmail_token_configured": settings.gmail_token_json is not None,
                "gmail_recipient_configured": bool(settings.gmail_recipient),
                "whatsapp_configured": bool(
                    settings.whatsapp_access_token and settings.whatsapp_phone_number_id and settings.whatsapp_to
                ),
            },
        )

    if method == "POST" and path == "/run":
        try:
            body = _json_body(event)
        except ValueError as exc:
            return _json_response(400, {"error": str(exc)})

        if body.get("gmail_recipient"):
            settings = replace(settings, gmail_recipient=str(body["gmail_recipient"]))
        if body.get("alert_channels"):
            settings = replace(settings, alert_channels=tuple(str(channel).lower() for channel in body["alert_channels"]))

        send_alerts = bool(body.get("send_alerts", True))
        return _json_response(200, run_guardrail(settings, send_alerts=send_alerts))

    return _json_response(404, {"error": f"No route for {method} {path}"})


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    if _is_http_api_event(event):
        return _handle_http_api_event(event)
    return run_guardrail(load_settings(), send_alerts=True)


if __name__ == "__main__":
    print(json.dumps(run_guardrail(), indent=2))
