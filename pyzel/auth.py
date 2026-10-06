from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from .exceptions import AuthenticationError, ChannelError


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_channels(channel: str | None = None, channels: Sequence[str] | None = None) -> list[str]:
    values: list[str] = []
    if channels:
        values.extend(str(item).strip() for item in channels if str(item).strip())
    clean_channel = _clean_optional(channel)
    if clean_channel and clean_channel not in values:
        values.append(clean_channel)
    if not values:
        raise ChannelError("at least one channel is required")
    return values


def create_production_auth_token(
    *,
    issuer: str,
    signing_key: str,
    expires_in: int = 3600,
    now: int | None = None,
) -> tuple[str, int]:
    """Create a short-lived RS256 auth token.

    This mirrors the production auth shape used by server-side Zello clients.
    The signing key must come from local configuration and is never logged.
    """

    clean_issuer = _clean_optional(issuer)
    clean_key = signing_key.strip() if isinstance(signing_key, str) else None
    if not clean_issuer or not clean_key:
        raise AuthenticationError("issuer and signing_key are required")

    try:
        import jwt
    except Exception as exc:  # pragma: no cover - dependency guard
        raise AuthenticationError("PyJWT is required for production auth") from exc

    issued_at = int(now if now is not None else time.time())
    expires_at = issued_at + int(expires_in)
    token = jwt.encode(
        {"iss": clean_issuer, "iat": issued_at, "exp": expires_at},
        clean_key,
        algorithm="RS256",
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token, expires_at


def build_logon_payload(
    *,
    channel: str | None = None,
    channels: Sequence[str] | None = None,
    username: str | None = None,
    password: str | None = None,
    auth_token: str | None = None,
    refresh_token: str | None = None,
    listen_only: bool = False,
) -> dict[str, Any]:
    """Build a Zello Channel API logon payload.

    Zello logon uses ``channels`` as an array of channel names. Later commands
    such as text messages use singular ``channel``.
    """

    payload: dict[str, Any] = {
        "command": "logon",
        "channels": _clean_channels(channel=channel, channels=channels),
    }

    if listen_only:
        payload["listen_only"] = True

    clean_refresh_token = _clean_optional(refresh_token)
    clean_auth_token = _clean_optional(auth_token)
    clean_username = _clean_optional(username)

    if clean_refresh_token:
        payload["refresh_token"] = clean_refresh_token
        return payload

    if clean_auth_token:
        payload["auth_token"] = clean_auth_token
        if clean_username:
            payload["username"] = clean_username
        if password:
            payload["password"] = password
        return payload

    if clean_username and password:
        payload["username"] = clean_username
        payload["password"] = password
        return payload

    raise AuthenticationError(
        "username/password, auth_token, or refresh_token is required"
    )


def build_text_message_payload(*, text: str, channel: str) -> dict[str, Any]:
    """Build a text-message payload for a channel."""

    clean_channel = _clean_optional(channel)
    if not clean_channel:
        raise ChannelError("channel is required")

    if text is None or str(text) == "":
        raise ValueError("text is required")

    return {
        "command": "send_text_message",
        "channel": clean_channel,
        "text": str(text),
    }


def build_ping_payload() -> dict[str, str]:
    """Build a keepalive ping payload."""

    return {"command": "ping"}
