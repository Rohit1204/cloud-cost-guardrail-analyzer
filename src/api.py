from __future__ import annotations

from dataclasses import replace

from fastapi import FastAPI
from fastapi import Query
from pydantic import BaseModel, Field

from app import _alert_run_response
from app import _cost_summary
from app import _recommendation_response
from app import run_guardrail
from aws_clients import AwsClientFactory
from config import Settings
from config import load_settings

api = FastAPI(
    title="Cloud Cost Guardrail Bot",
    description="Local API for running AWS cost guardrail checks and sending alerts.",
    version="0.1.0",
)


class RunRequest(BaseModel):
    send_alerts: bool = Field(default=True, description="Send Gmail/WhatsApp notifications for findings.")
    cost_months: int = Field(default=1, ge=1, le=12, description="Cost summary window in months.")
    gmail_recipient: str | None = Field(default=None, description="Override the configured Gmail recipient.")
    alert_channels: list[str] | None = Field(
        default=None,
        description="Override alert channels for this run. Example: ['gmail'].",
    )


@api.get("/health")
def health() -> dict[str, object]:
    settings = load_settings()
    return {
        "status": "ok",
        "target_region": settings.aws_region,
        "alert_channels": settings.alert_channels,
        "gmail_token_configured": settings.gmail_token_json is not None,
        "gmail_recipient_configured": bool(settings.gmail_recipient),
        "whatsapp_configured": bool(
            settings.whatsapp_access_token and settings.whatsapp_phone_number_id and settings.whatsapp_to
        ),
    }


@api.get("/costs/summary")
def cost_summary(months: int = Query(default=1, ge=1, le=12)) -> dict[str, object]:
    settings = load_settings()
    summary, error = _cost_summary(AwsClientFactory(settings.aws_region), months=months)
    return {"cost_summary": summary, "errors": [error] if error else []}


@api.get("/recommendations")
def recommendations(months: int = Query(default=1, ge=1, le=12)) -> dict[str, object]:
    settings = load_settings()
    return _recommendation_response(settings, send_alerts=False, cost_months=months)


@api.post("/alerts/run")
def run_alerts(request: RunRequest | None = None) -> dict[str, object]:
    request = request or RunRequest()
    settings = _settings_with_overrides(request)
    return _alert_run_response(settings, cost_months=request.cost_months)


@api.post("/run")
def run(request: RunRequest | None = None) -> dict[str, object]:
    request = request or RunRequest()
    settings = _settings_with_overrides(request)
    return run_guardrail(settings, send_alerts=request.send_alerts, cost_months=request.cost_months)


def _settings_with_overrides(request: RunRequest) -> Settings:
    settings = load_settings()

    if request.gmail_recipient:
        settings = replace(settings, gmail_recipient=request.gmail_recipient)
    if request.alert_channels:
        settings = replace(settings, alert_channels=tuple(channel.lower() for channel in request.alert_channels))

    return settings
