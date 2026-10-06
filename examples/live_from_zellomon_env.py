import asyncio
import json
import os
from pathlib import Path
from typing import Any

from pyzel import ZelloClient, sanitize_for_log


def _read_file(path_value: str | None) -> str | None:
    if not path_value:
        return None
    return Path(path_value).expanduser().read_text(encoding="utf-8")


def _pick(config: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = config.get(name)
        if value not in (None, ""):
            return value
    return None


def _load_accounts() -> dict[str, Any]:
    raw = os.getenv("ZELLO_ACCOUNTS")
    if not raw:
        raise RuntimeError("Missing ZELLO_ACCOUNTS environment variable")
    data = json.loads(raw)
    if isinstance(data, list):
        return {str(item.get("account_name") or item.get("name") or index): item for index, item in enumerate(data)}
    if isinstance(data, dict):
        return data
    raise RuntimeError("ZELLO_ACCOUNTS must be a JSON object or list")


def _select_account(accounts: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    requested = os.getenv("PYZEL_ACCOUNT") or os.getenv("ZELLO_ACCOUNT")
    if requested:
        if requested not in accounts:
            raise RuntimeError(f"Account not found in ZELLO_ACCOUNTS: {requested}")
        return requested, accounts[requested]
    first_name = next(iter(accounts))
    return first_name, accounts[first_name]


def _channels(config: dict[str, Any]) -> tuple[str, list[str]]:
    channels_value = config.get("channels") or []
    if isinstance(channels_value, str):
        channels = [channels_value]
    else:
        channels = [str(item).strip() for item in channels_value if str(item).strip()]

    primary = _pick(config, "channel_name", "zello_channel", "channel")
    if primary:
        primary = str(primary).strip()
        if primary and primary not in channels:
            channels.insert(0, primary)
    if not channels:
        raise RuntimeError("Selected account has no channel_name, zello_channel, channel, or channels")
    return channels[0], channels


async def main() -> int:
    if os.getenv("PYZEL_LIVE_TEST") != "1":
        print("Refusing to run live test. Set PYZEL_LIVE_TEST=1 locally first.")
        return 2

    accounts = _load_accounts()
    account_name, account = _select_account(accounts)
    channel, channels = _channels(account)

    username = _pick(account, "auth_username", "zello_username", "username")
    password = _pick(account, "password", "zello_password")
    auth_token = _pick(account, "auth_token", "raw_token")
    refresh_token = _pick(account, "refresh_token")
    issuer = _pick(account, "issuer")
    signing_key = _pick(account, "private_key", "signing_key") or _read_file(
        _pick(account, "private_key_file", "signing_key_file")
    )

    print("Selected account:", account_name)
    print("Selected channels:", channels)

    client = ZelloClient(
        username=username,
        password=password,
        auth_token=auth_token,
        refresh_token=refresh_token,
        issuer=issuer,
        signing_key=signing_key,
        endpoint=os.getenv("ZELLO_ENDPOINT", "wss://zello.io/ws"),
        channel=channel,
        channels=channels,
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
