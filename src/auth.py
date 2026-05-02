from __future__ import annotations

from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from config import Settings


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


def _bearer_token(headers: dict[str, str]) -> str:
    authorization = headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Missing Google sign-in token")
    return token


def verify_google_user(settings: Settings, headers: dict[str, str]) -> dict[str, Any] | None:
    if not settings.google_client_id:
        return None

    token = _bearer_token(headers)
    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), settings.google_client_id)
    except ValueError as exc:
        raise AuthError("Invalid Google sign-in token") from exc

    email = str(claims.get("email", "")).strip().lower()
    if not email:
        raise AuthError("Google sign-in token does not include an email")

    allowed = {allowed_email.strip().lower() for allowed_email in settings.auth_allowed_emails if allowed_email.strip()}
    if not allowed:
        raise AuthError("Sign-in is not configured.", status_code=403)
    if email not in allowed:
        raise AuthError("This email is not authorized to sign in.", status_code=403)

    return claims
