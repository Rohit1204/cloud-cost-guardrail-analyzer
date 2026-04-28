from __future__ import annotations

import requests

from config import Settings
from models import NotificationResult, Recommendation
from notifiers.message_builder import build_body


def send_whatsapp_alert(settings: Settings, recommendations: list[Recommendation]) -> NotificationResult:
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id or not settings.whatsapp_to:
        return NotificationResult("whatsapp", False, "WhatsApp token, phone number id, or recipient is not configured")

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    body = build_body(recommendations)
    if len(body) > 3900:
        body = body[:3800] + "\n\nMessage truncated. Check Gmail or CloudWatch Logs for full details."

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {settings.whatsapp_access_token}", "Content-Type": "application/json"},
        json={
            "messaging_product": "whatsapp",
            "to": settings.whatsapp_to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        },
        timeout=10,
    )
    if response.status_code >= 300:
        return NotificationResult("whatsapp", False, f"Meta API error {response.status_code}: {response.text}")
    return NotificationResult("whatsapp", True, "Sent WhatsApp alert")
