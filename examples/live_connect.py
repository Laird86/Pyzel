import asyncio
import os
from pathlib import Path

from pyzel import ZelloClient, sanitize_for_log


def _read_file(path_value):
    if not path_value:
        return None
    return Path(path_value).expanduser().read_text(encoding="utf-8")


async def main() -> int:
    """Run a local-only live WebSocket smoke test.

    This script is intentionally guarded so it cannot accidentally run in CI.
    Set PYZEL_LIVE_TEST=1 locally before using it.
    """

    if os.getenv("PYZEL_LIVE_TEST") != "1":
        print("Refusing to run live test. Set PYZEL_LIVE_TEST=1 locally first.")
        return 2

    channel = os.getenv("ZELLO_CHANNEL")
    endpoint = os.getenv("ZELLO_ENDPOINT", "wss://zello.io/ws")
    username = os.getenv("ZELLO_USERNAME") or None
    password = os.getenv("ZELLO_PASSWORD") or None
    auth_token = os.getenv("ZELLO_AUTH_TOKEN") or None
    refresh_token = os.getenv("ZELLO_REFRESH_TOKEN") or None
    issuer = os.getenv("ZELLO_ISSUER") or None
    signing_key = os.getenv("ZELLO_SIGNING_KEY") or _read_file(os.getenv("ZELLO_SIGNING_KEY_FILE"))

    if not channel:
        print("Missing ZELLO_CHANNEL.")
        return 2

    if auth_token and auth_token.strip().startswith("-----BEGIN"):
        print("Refusing to use a PEM block as ZELLO_AUTH_TOKEN.")
        return 2

    if refresh_token and refresh_token.strip().startswith("-----BEGIN"):
        print("Refusing to use a PEM block as ZELLO_REFRESH_TOKEN.")
        return 2

    has_production_auth = bool(issuer and signing_key)
    if not refresh_token and not auth_token and not has_production_auth and not (username and password):
        print("Missing credentials. Set username/password, token, refresh token, or issuer/signing key locally.")
        return 2

    client = ZelloClient(
        username=username,
        password=password,
        auth_token=auth_token,
        refresh_token=refresh_token,
        issuer=issuer,
        signing_key=signing_key,
        endpoint=endpoint,
    )

    try:
        await client.connect(open_socket=True)
        logon_payload = await client.join_channel(channel)
        print("Sent logon payload:", sanitize_for_log(logon_payload))

        response = await client.receive()
        print("First response:", sanitize_for_log(response))
    finally:
        await client.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
