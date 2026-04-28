from __future__ import annotations

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
from notifiers.gmail import send_gmail_alert
from notifiers.whatsapp import send_whatsapp_alert
from recommendations import build_recommendations

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _notify(settings: Any, recommendations: Any) -> list[NotificationResult]:
    results: list[NotificationResult] = []
    if "gmail" in settings.alert_channels:
        try:
            results.append(send_gmail_alert(settings, recommendations))
        except Exception as exc:  # Lambda should report one channel failure without hiding all findings.
            logger.exception("Gmail notification failed")
            results.append(NotificationResult("gmail", False, str(exc)))
    if "whatsapp" in settings.alert_channels:
        try:
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


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    return run_guardrail(load_settings(), send_alerts=True)


if __name__ == "__main__":
    print(json.dumps(run_guardrail(), indent=2))
