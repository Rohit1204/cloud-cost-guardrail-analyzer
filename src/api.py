from __future__ import annotations

from dataclasses import replace

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app import run_guardrail
from config import load_settings

api = FastAPI(
    title="Cloud Cost Guardrail Bot",
    description="Local API for running AWS cost guardrail checks and sending alerts.",
    version="0.1.0",
)


class RunRequest(BaseModel):
    send_alerts: bool = Field(default=True, description="Send Gmail/WhatsApp notifications for findings.")
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


@api.post("/run")
def run(request: RunRequest | None = None) -> dict[str, object]:
    request = request or RunRequest()
    settings = load_settings()

    if request.gmail_recipient:
        settings = replace(settings, gmail_recipient=request.gmail_recipient)
    if request.alert_channels:
        settings = replace(settings, alert_channels=tuple(channel.lower() for channel in request.alert_channels))

    return run_guardrail(settings, send_alerts=request.send_alerts)
