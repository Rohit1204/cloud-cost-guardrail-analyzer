from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

import boto3

from config import Settings

STATUS_NEW = "new"
STATUS_ACKNOWLEDGED = "acknowledged"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESOLVED = "resolved"
ALLOWED_STATUSES = {STATUS_NEW, STATUS_ACKNOWLEDGED, STATUS_IN_PROGRESS, STATUS_RESOLVED}


def recommendation_id(recommendation: dict[str, Any]) -> str:
    finding = recommendation.get("finding", {})
    parts = [
        str(finding.get("category", "")),
        str(finding.get("resource_type", "")),
        str(finding.get("resource_id", "")),
        str(recommendation.get("action", "")),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _client(settings: Settings) -> Any:
    return boto3.client("dynamodb", region_name=settings.aws_region)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_statuses(settings: Settings, recommendation_ids: list[str]) -> dict[str, str]:
    if not settings.recommendation_status_table or not recommendation_ids:
        return {}

    unique_ids = sorted(set(recommendation_ids))
    response = _client(settings).batch_get_item(
        RequestItems={
            settings.recommendation_status_table: {
                "Keys": [{"recommendation_id": {"S": recommendation_id}} for recommendation_id in unique_ids],
                "ProjectionExpression": "recommendation_id,#status",
                "ExpressionAttributeNames": {"#status": "status"},
            }
        }
    )
    items = response.get("Responses", {}).get(settings.recommendation_status_table, [])
    return {
        item["recommendation_id"]["S"]: item.get("status", {}).get("S", STATUS_NEW)
        for item in items
        if item.get("recommendation_id", {}).get("S")
    }


def enrich_recommendations(settings: Settings, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    ids = [recommendation_id(recommendation) for recommendation in recommendations]
    statuses = load_statuses(settings, ids)

    for recommendation, rec_id in zip(recommendations, ids, strict=True):
        enriched.append(
            {
                **recommendation,
                "recommendation_id": rec_id,
                "status": statuses.get(rec_id, STATUS_NEW),
            }
        )
    return enriched


def update_status(settings: Settings, recommendation_id_value: str, status: str) -> dict[str, str]:
    normalized_status = status.strip().lower()
    if normalized_status not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")
    if not recommendation_id_value:
        raise ValueError("recommendation_id is required")
    if not settings.recommendation_status_table:
        raise RuntimeError("recommendation status table is not configured")

    updated_at = _now_iso()
    _client(settings).put_item(
        TableName=settings.recommendation_status_table,
        Item={
            "recommendation_id": {"S": recommendation_id_value},
            "status": {"S": normalized_status},
            "updated_at": {"S": updated_at},
        },
    )
    return {
        "recommendation_id": recommendation_id_value,
        "status": normalized_status,
        "updated_at": updated_at,
    }
