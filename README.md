# Pyzel

> **Release candidate / unofficial project.** Pyzel is independently developed and is not endorsed by, affiliated with, or maintained by Zello. The Zello name is used only to identify the API and services this library interoperates with.

Async Python client for the public Zello Channel API.

The package is intentionally small. It provides WebSocket connection handling, logon payload helpers, text-message support, event callbacks, refresh-token support, and optional server-side JWT generation helpers.

## Status

Alpha. The package API may change before 1.0.

This repository is kept separate from Zellomon. Publishing or changing this package must not require changes to Zellomon's production authentication path.

## Supported API targets

The upstream Channel API documents three endpoints:

- Zello Friends & Family: `wss://zello.io/ws`
- Zello Work: `wss://zellowork.io/ws/<network name>`
- Zello Enterprise Server: `wss://<server domain>/ws/mesh`

Friends & Family requires an API auth token or refresh token. Named users also provide username/password. Zello Work uses username/password and should omit the Friends & Family auth token.

See the upstream specification: https://github.com/zelloptt/zello-channel-api

## Installation

For local development:

```bash
python -m pip install -e ".[dev]"
```

For optional server-side JWT helpers:

```bash
python -m pip install -e ".[production-auth]"
```

A public PyPI install command should only be added after the distribution has actually been published.

## Quick start — Zello Work

```python
import asyncio
from pyzel import ZelloClient, sanitize_for_log

async def main():
    client = ZelloClient(
        username="operator",
        password="secret",
        endpoint="wss://zellowork.io/ws/example-network",
    )

    try:
        await client.connect(open_socket=True)
        await client.join_channel("Operations")
        first_event = await client.receive()
        print(sanitize_for_log(first_event))
    finally:
        await client.disconnect()

asyncio.run(main())
```

## Quick start — Friends & Family

Use a development token from the Zello developer portal or a short-lived production token issued by your own backend. Never embed a private signing key in a distributed application.

```python
import asyncio
from pyzel import ZelloClient, sanitize_for_log

async def main():
    client = ZelloClient(
        username="example-user",
        password="secret",
        auth_token="short-lived-token",
    )

    try:
        await client.connect(open_socket=True)
        await client.join_channel("ExampleChannel")
        response = await client.receive()
        print(sanitize_for_log(response))
    finally:
        await client.disconnect()

asyncio.run(main())
```

## Safe logging

A successful Friends & Family logon can return a refresh token. Do not print raw authentication responses.

```python
from pyzel import sanitize_for_log

print(sanitize_for_log(response))
```

The bundled live examples use the same recursive redaction helper.

## Live smoke test

Live tests are intentionally opt-in and should use local environment variables, never committed credentials.

```bash
export PYZEL_LIVE_TEST=1
export ZELLO_CHANNEL=ExampleChannel
export ZELLO_USERNAME=example-user
export ZELLO_PASSWORD='...'
export ZELLO_AUTH_TOKEN='...'
python examples/live_connect.py
```

For Zello Work, set `ZELLO_ENDPOINT` to your network-specific endpoint and omit `ZELLO_AUTH_TOKEN`.

## Security

- Never commit passwords, auth tokens, refresh tokens, API keys, JWT signing keys, or private keys.
- Zello's upstream authentication documentation says production JWT signing keys belong on a trusted server, not inside a client application.
- `.env`, PEM files, key files, and common certificate/key formats are ignored by Git.
- Live examples require `PYZEL_LIVE_TEST=1` so CI cannot accidentally authenticate to a real account.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
python -m twine check dist/*
```

CI tests supported Python versions and validates that source and wheel distributions build cleanly.

## Related project: Zellomon

Pyzel is a standalone Python client for the Zello Channel API. It is also used as a reusable integration layer alongside **Zellomon**, a separate Zello operations, monitoring, compliance, alerting, transcription, and intelligence platform developed by ZBots.

Learn more about ZBots and Zellomon at https://zbots.co.uk.

For Pyzel questions, integration discussions, or commercial enquiries, contact **bruce@zbots.co.uk**.

## Trademark note

Zello is a trademark of Zello Inc. This project must not imply official status or endorsement. Pyzel is the project and distribution name. Zello is referenced only to describe compatibility with the Zello Channel API; no endorsement or affiliation is implied.
