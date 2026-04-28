from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    aws_region: str
    lookback_days: int
    idle_cpu_threshold: float
    idle_db_connection_threshold: float
    spend_spike_multiplier: float
    spend_spike_min_usd: float
    high_cost_service_threshold_usd: float
    alert_channels: tuple[str, ...]
    gmail_sender: str | None
    gmail_recipient: str | None
    gmail_token_json: dict[str, Any] | None
    owner_tag_keys: tuple[str, ...]
    environment_tag_keys: tuple[str, ...]
    owner_email_map: dict[str, str]
    default_owner_email: str | None
    default_environment: str | None
    whatsapp_access_token: str | None
    whatsapp_phone_number_id: str | None
    whatsapp_to: str | None
    whatsapp_api_version: str


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _get_json(name: str) -> dict[str, Any] | None:
    raw = os.getenv(name)
    if not raw:
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must be a JSON object")
    return parsed


def _get_json_file(name: str, default_path: str) -> dict[str, Any] | None:
    path = Path(os.getenv(name, default_path)).expanduser()
    if not path.exists():
        return None
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return parsed


def _channels() -> tuple[str, ...]:
    raw = os.getenv("ALERT_CHANNELS", "gmail,whatsapp")
    return tuple(channel.strip().lower() for channel in raw.split(",") if channel.strip())


def _csv(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def load_settings() -> Settings:
    owner_email_map = _get_json("OWNER_EMAIL_MAP") or {}
    return Settings(
        aws_region=os.getenv("TARGET_AWS_REGION") or os.getenv("AWS_REGION", "ap-south-1"),
        lookback_days=_get_int("LOOKBACK_DAYS", 7),
        idle_cpu_threshold=_get_float("IDLE_CPU_THRESHOLD", 5.0),
        idle_db_connection_threshold=_get_float("IDLE_DB_CONNECTION_THRESHOLD", 1.0),
        spend_spike_multiplier=_get_float("SPEND_SPIKE_MULTIPLIER", 1.5),
        spend_spike_min_usd=_get_float("SPEND_SPIKE_MIN_USD", 25.0),
        high_cost_service_threshold_usd=_get_float("HIGH_COST_SERVICE_THRESHOLD_USD", 100.0),
        alert_channels=_channels(),
        gmail_sender=os.getenv("GMAIL_SENDER"),
        gmail_recipient=os.getenv("GMAIL_RECIPIENT"),
        gmail_token_json=_get_json("GMAIL_TOKEN_JSON") or _get_json_file("GMAIL_TOKEN_FILE", "gmail_token.json"),
        owner_tag_keys=_csv("OWNER_TAG_KEYS", "OwnerEmail,owner_email,Owner,owner,Team,team"),
        environment_tag_keys=_csv("ENVIRONMENT_TAG_KEYS", "Environment,environment,Env,env,Stage,stage"),
        owner_email_map={str(key): str(value) for key, value in owner_email_map.items()},
        default_owner_email=os.getenv("DEFAULT_OWNER_EMAIL"),
        default_environment=os.getenv("DEFAULT_ENVIRONMENT"),
        whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN"),
        whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
        whatsapp_to=os.getenv("WHATSAPP_TO"),
        whatsapp_api_version=os.getenv("WHATSAPP_API_VERSION", "v19.0"),
    )
