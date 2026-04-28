from __future__ import annotations

import base64
from collections import defaultdict
from dataclasses import replace
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import Settings
from models import NotificationResult, Recommendation
from notifiers.message_builder import build_body, build_subject

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def _recipient_for(recommendation: Recommendation, settings: Settings) -> str | None:
    return recommendation.finding.metadata.get("owner_email") or settings.gmail_recipient


def _group_by_recipient(
    recommendations: list[Recommendation], settings: Settings
) -> dict[str, list[Recommendation]]:
    grouped: dict[str, list[Recommendation]] = defaultdict(list)
    for recommendation in recommendations:
        recipient = _recipient_for(recommendation, settings)
        if recipient:
            grouped[recipient].append(recommendation)
    return dict(grouped)


def _send_gmail_message(settings: Settings, recommendations: list[Recommendation], recipient: str) -> str:
    credentials = Credentials.from_authorized_user_info(settings.gmail_token_json, scopes=[GMAIL_SEND_SCOPE])
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    routed_settings = replace(settings, gmail_recipient=recipient)
    message = MIMEText(build_body(recommendations), "plain", "utf-8")
    message["to"] = routed_settings.gmail_recipient
    message["from"] = routed_settings.gmail_sender or "me"
    message["subject"] = build_subject(recommendations)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    result = service.users().messages().send(userId=routed_settings.gmail_sender or "me", body={"raw": encoded}).execute()
    return result.get("id", "unknown")


def send_gmail_alert(settings: Settings, recommendations: list[Recommendation]) -> NotificationResult:
    if not settings.gmail_token_json:
        return NotificationResult("gmail", False, "Gmail token is not configured")

    grouped = _group_by_recipient(recommendations, settings)
    if not grouped:
        return NotificationResult("gmail", False, "Gmail token or recipient is not configured")

    message_ids = [
        _send_gmail_message(settings, recipient_recommendations, recipient)
        for recipient, recipient_recommendations in grouped.items()
    ]
    return NotificationResult(
        "gmail",
        True,
        f"Sent {len(message_ids)} Gmail message(s) to {len(grouped)} owner route(s): {', '.join(sorted(grouped))}",
    )
