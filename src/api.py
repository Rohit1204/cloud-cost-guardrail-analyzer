from __future__ import annotations

from dataclasses import replace

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from pydantic import BaseModel, Field

from app import _alert_run_response
from app import _cost_summary
from app import _recommendation_response
from app import run_guardrail
from auth import AuthError
from auth import verify_google_user
from aws_clients import AwsClientFactory
from billing_console import billing_console_federation_url
from config import Settings
from config import load_settings
from recommendation_status import update_status

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


class StatusRequest(BaseModel):
    recommendation_id: str = Field(description="Stable recommendation id returned by GET /recommendations.")
    status: str = Field(description="One of: new, acknowledged, in_progress, resolved.")


def require_user(request: Request) -> dict[str, object] | None:
    settings = load_settings()
    try:
        return verify_google_user(settings, {key.lower(): value for key, value in request.headers.items()})
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@api.get("/health")
def health(user: dict[str, object] | None = Depends(require_user)) -> dict[str, object]:
    settings = load_settings()
    return {
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
    }


@api.get("/billing/console-url")
def billing_console_url(user: dict[str, object] | None = Depends(require_user)) -> dict[str, str]:
    settings = load_settings()
    try:
        url = billing_console_federation_url(settings, user)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"url": url}


@api.get("/costs/summary")
def cost_summary(months: int = Query(default=1, ge=1, le=12), user: dict[str, object] | None = Depends(require_user)) -> dict[str, object]:
    settings = load_settings()
    summary, error = _cost_summary(
        AwsClientFactory(settings.aws_region),
        months=months,
        invoice_summary_enabled=settings.invoice_summary_enabled,
    )
    return {"cost_summary": summary, "errors": [error] if error else []}


@api.get("/recommendations")
def recommendations(months: int = Query(default=1, ge=1, le=12), user: dict[str, object] | None = Depends(require_user)) -> dict[str, object]:
    settings = load_settings()
    return _recommendation_response(settings, send_alerts=False, cost_months=months)


@api.patch("/recommendations/status")
def recommendation_status(request: StatusRequest, user: dict[str, object] | None = Depends(require_user)) -> dict[str, str]:
    settings = load_settings()
    try:
        return update_status(settings, request.recommendation_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@api.post("/alerts/run")
def run_alerts(request: RunRequest | None = None, user: dict[str, object] | None = Depends(require_user)) -> dict[str, object]:
    request = request or RunRequest()
    settings = _settings_with_overrides(request)
    return _alert_run_response(settings, cost_months=request.cost_months)


@api.post("/run")
def run(request: RunRequest | None = None, user: dict[str, object] | None = Depends(require_user)) -> dict[str, object]:
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
