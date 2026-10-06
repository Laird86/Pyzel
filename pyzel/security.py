from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REDACTED = "<redacted>"

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "api_key",
        "auth_token",
        "authorization",
        "client_secret",
        "developer_token",
        "media_encryption_key",
        "password",
        "private_key",
        "refresh_token",
        "sample_development_token",
        "secret",
        "signing_key",
    }
)


def sanitize_for_log(value: Any) -> Any:
    """Return a log-safe representation of a value.

    Known credential fields are redacted recursively. Binary payloads are
    replaced with a size-only placeholder so voice data is not dumped to logs.
    """

    if isinstance(value, Mapping):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in SENSITIVE_FIELD_NAMES:
                sanitized[key] = REDACTED
            else:
                sanitized[key] = sanitize_for_log(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_for_log(item) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_for_log(item) for item in value)

    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<binary {len(value)} bytes>"

    return value
