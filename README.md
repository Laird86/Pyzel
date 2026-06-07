# PyZello SDK

A clean, robust, and asynchronous Python SDK for interacting with the **Zello Channel WebSocket API**.

## Features

- **Asynchronous Design**: Built on top of `asyncio` and `websockets` for high-performance integrations.
- **Robust Reconnection**: Contains continuous background loops that automatically recover from dropped connections.
- **Production Ready**: Supports secure JSON Web Token (JWT) generating out-of-the-box using the Zello issuer and private key standard.
- **Multiple Channels**: Easily listen to and interact with multiple Zello channels concurrently.
- **Private & Channel Messaging**: Send text messages to channels or directly format private messages to individual users.

## Installation

You can install the SDK locally or build it for PyPI.

```bash
# To install locally
pip install -e .

# Or, if published to PyPI later
# pip install pyzello
```

## Quick Start

```python
import asyncio
import logging
from pyzello import ZelloClient

logging.basicConfig(level=logging.INFO)

async def main():
    # 1. Setup your configuration
    config = {
        "auth_mode": "production",
        "issuer": "YOUR_ZELLO_ISSUER_ID",
        "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        "zello_channels": ["TestChannel1", "Intercom"]
    }

    # 2. Initialize the client
    client = ZelloClient(api_config=config)

    # 3. Register Event Callbacks
    def on_connect():
        print("Connected to Zello!")
        
    def on_message(event):
        print(f"Received Zello Event: {event}")

    client.on_connect = on_connect
    client.on_event = on_message

    # 4. Connect to Zello (this runs in a loop reconnecting automatically)
    # Run it concurrently if you want to perform other actions
    asyncio.create_task(client.connect())
    
    # Wait to ensure connection
    await asyncio.sleep(5)
    
    # 5. Send a text message to a channel
    await client.send_text_message("Hello from PyZello SDK!", "TestChannel1")
    
    # Keep application alive
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Event Callbacks Available

You can map functions directly to the client to respond to specific events:

- `on_connect()`: Triggered upon successful authentication.
- `on_disconnect()`: Triggered when the WebSocket drops.
- `on_error(message: str)`: Triggered via terminal errors.
- `on_event(event_dict: dict)`: Receives general JSON commands from Zello.
- `on_audio_packet(audio_bytes: bytes)`: Triggered continually when binary audio streams arrive.
- `on_channel_status_update(status_dict: dict)`: Status changes over a specific channel.
- `on_contacts_list(users_dict: dict)`: Delivers the contacts list.

## Publishing to PyPI (For Maintainers)

1. Make sure you have `twine` installed: `pip install twine wheel setuptools`
2. Build the distribution: `python setup.py sdist bdist_wheel`
3. Upload to PyPI: `twine upload dist/*`
