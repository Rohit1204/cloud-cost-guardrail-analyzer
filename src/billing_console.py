from __future__ import annotations

import json
import logging
import re
import urllib.parse
from typing import Any

import boto3
import requests
from botocore.exceptions import ClientError

from config import Settings

logger = logging.getLogger(__name__)

_FEDERATION_BASE = "https://signin.aws.amazon.com/federation"
_DEFAULT_BILLING_DESTINATION = "https://console.aws.amazon.com/billing/home#/"
_ISSUER = "cloud-cost-guardrail-bot"


def _safe_session_name(email: str | None) -> str:
    raw = email or "guardrail-user"
    cleaned = re.sub(r"[^a-zA-Z0-9_=,.@-]", "-", raw)
    return cleaned[:64] or "guardrail-session"


def _signin_token(access_key: str, secret_key: str, session_token: str) -> str:
    session_json = json.dumps(
        {
            "sessionId": access_key,
            "sessionKey": secret_key,
            "sessionToken": session_token,
        },
        separators=(",", ":"),
    )
    response = requests.get(
        _FEDERATION_BASE,
        params={"Action": "getSigninToken", "Session": session_json},
        timeout=15,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    token = payload.get("SigninToken")
    if not token or not isinstance(token, str):
        raise RuntimeError("Federation did not return SigninToken")
    return token


def _login_url(*, signin_token: str, destination: str) -> str:
    query = urllib.parse.urlencode(
        {
            "Action": "login",
            "Issuer": _ISSUER,
            "Destination": destination,
            "SigninToken": signin_token,
        }
    )
    return f"{_FEDERATION_BASE}?{query}"


def billing_console_federation_url(settings: Settings, user: dict[str, object] | None) -> str:
    """Assume the billing console role and return an AWS console login URL (Billing destination)."""
    role_arn = settings.billing_console_role_arn
    if not role_arn:
        raise ValueError("Billing console federation is not configured (missing BILLING_CONSOLE_ROLE_ARN)")

    email = user.get("email") if user else None
    email_str = str(email) if email else None

    sts = boto3.client("sts", region_name=settings.aws_region)
    try:
        assumed = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=_safe_session_name(email_str),
            DurationSeconds=900,
        )
    except ClientError as exc:
        logger.warning("sts:AssumeRole failed for billing console: %s", exc)
        raise RuntimeError("Unable to assume billing console role") from exc

    creds = assumed["Credentials"]
    token = _signin_token(
        creds["AccessKeyId"],
        creds["SecretAccessKey"],
        creds["SessionToken"],
    )
    return _login_url(signin_token=token, destination=_DEFAULT_BILLING_DESTINATION)
