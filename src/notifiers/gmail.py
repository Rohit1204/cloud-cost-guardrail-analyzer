from __future__ import annotations

import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import Settings
from models import NotificationResult, Recommendation
from notifiers.message_builder import build_body, build_subject

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def send_gmail_alert(settings: Settings, recommendations: list[Recommendation]) -> NotificationResult:
    if not settings.gmail_token_json or not settings.gmail_recipient:
        return NotificationResult("gmail", False, "Gmail token or recipient is not configured")

    credentials = Credentials.from_authorized_user_info(settings.gmail_token_json, scopes=[GMAIL_SEND_SCOPE])
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    message = MIMEText(build_body(recommendations), "plain", "utf-8")
    message["to"] = settings.gmail_recipient
    message["from"] = settings.gmail_sender or "me"
    message["subject"] = build_subject(recommendations)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    result = service.users().messages().send(userId=settings.gmail_sender or "me", body={"raw": encoded}).execute()
    return NotificationResult("gmail", True, f"Sent Gmail message {result.get('id', 'unknown')}")
