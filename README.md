# PyZello SDK

> **Disclaimer**: This is an unofficial community project and is NOT officially affiliated with, endorsed by, or maintained by Zello Inc.

A modern, robust, and completely asynchronous Python SDK for interacting with the **Zello Channel WebSocket API**.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Modern Developer Experience**: Employs elegant decorators (`@client.on`) similar to Discord.py or Flask.
- **Asynchronous & Fast**: Built natively on `asyncio` and `websockets` for high-throughput, non-blocking audio and data streaming.
- **Robust Reconnection**: Contains a resilient background loop that automatically recovers from dropped sockets or network interruptions.
- **Production Ready Auth**: Built-in support for securely generating short-lived JSON Web Tokens (JWT) using Zello's issuer/private key standards.
- **Context Manager Support**: Clean connection management using `async with ZelloClient(config) as client:`

## Installation

You can install PyZello via PIP:

```bash
# To install from source locally:
pip install -e .

# Or, if published to PyPI later:
# pip install pyzello
```

## Quick Start: The "Echo Bot"

Getting an interactive bot up and running takes less than 30 lines of code.

```python
import asyncio
from pyzello import ZelloClient

config = {
    "auth_mode": "development",      # Use 'production' for JWT signing
    "auth_token": "YOUR_DEV_TOKEN",
    "zello_username": "YOUR_USERNAME",
    "zello_channels": ["TestChannel"]
}

client = ZelloClient(api_config=config)

@client.on("connect")
async def on_connect():
    print("Bot is successfully connected to Zello!")

@client.on("on_text_message")
async def handle_message(event):
    channel = event.get("channel")
    sender = event.get("from")
    text = event.get("text", "")

    # Prevent infinite echo loops
    if sender == config["zello_username"]:
        return

    print(f"[{channel}] {sender}: {text}")
    
    # Reply to the channel
    await client.send_text_message(f"Echoing back: {text}", channel)

if __name__ == "__main__":
    # Start the robust reconnection loop and event dispatcher
    asyncio.run(client.start())
```

## Available Events

The `@client.on("event_name")` decorator automatically maps Zello WebSocket commands to your functions. Common events include:

- `"connect"`: Triggered upon successful authentication with Zello.
- `"disconnect"`: Triggered when the WebSocket drops.
- `"error"`: Supplies string error messages when authentication or networking fails.
- `"on_text_message"`: Received a text message.
- `"on_channel_status"`: Notifies when user counts or statuses change.
- `"on_users_list"`: Delivers the contact list state.
- `"on_stream_start"`: Someone started transmitting audio.
- `"audio_packet"`: Yields raw `bytes` for an active voice stream.
- `"any_event"`: A wildcard trigger that passes the raw python dictionary of ANY JSON frame emitted.

## Dealing with Audio

To keep this SDK lightweight, audio decoding (e.g. `Opus` to `Wav` conversions) is intentionally *not* included. When someone broadcasts voice, PyZello emits `"audio_packet"` events containing raw binary network frames. You are free to route these raw bytes to an `opuslib` decoder or `FFmpeg` subprocess in your application.

## Advanced Usage: Context Managers

For script-based tools, you can use PyZello as an async context manager. This automatically starts the background connection task and cleans it up when the block exits.

```python
async def send_daily_alert():
    async with ZelloClient(api_config=config) as client:
        await client.send_text_message("Good morning, team!", "DailyStandup")
        
asyncio.run(send_daily_alert())
```

## Publishing to PyPI (For Maintainers)

1. Make sure you have `twine` installed: `pip install twine wheel setuptools`
2. Build the distribution: `python setup.py sdist bdist_wheel`
3. Upload to PyPI: `twine upload dist/*`
