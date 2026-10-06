from pyzel import sanitize_for_log


def test_sanitize_for_log_redacts_credentials_recursively():
    value = {
        "success": True,
        "refresh_token": "refresh-secret",
        "nested": {
            "auth_token": "auth-secret",
            "password": "password-secret",
            "safe": "visible",
        },
        "items": [{"private_key": "pem-secret"}, {"channel": "ExampleChannel"}],
    }

    sanitized = sanitize_for_log(value)

    assert sanitized["success"] is True
    assert sanitized["refresh_token"] == "<redacted>"
    assert sanitized["nested"]["auth_token"] == "<redacted>"
    assert sanitized["nested"]["password"] == "<redacted>"
    assert sanitized["nested"]["safe"] == "visible"
    assert sanitized["items"][0]["private_key"] == "<redacted>"
    assert sanitized["items"][1]["channel"] == "ExampleChannel"


def test_sanitize_for_log_does_not_dump_binary_audio():
    assert sanitize_for_log(b"audio-data") == "<binary 10 bytes>"


def test_sanitize_for_log_preserves_non_sensitive_fields():
    value = {
        "command": "logon",
        "channels": ["ExampleChannel"],
        "username": "example-user",
        "success": True,
    }

    assert sanitize_for_log(value) == value
