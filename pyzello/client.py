import json
import time
import asyncio
import logging
import traceback
from typing import Dict, List, Optional, Callable, Any

import websockets
import jwt

try:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter as CryptoCounter
except ImportError:
    pass

logger = logging.getLogger(__name__)

class ZelloClient:
    """
    A Python SDK client for the Zello Channel WebSocket API.
    Manages the WebSocket connection, authentication, and message handling.
    """
    def __init__(self, api_config: Dict[str, Any], loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Initializes the ZelloClient.

        Args:
            api_config (dict): Configuration dictionary containing credentials and settings.
            loop (asyncio.AbstractEventLoop, optional): The asyncio event loop. Defaults to None.
        """
        self.api_config = api_config
        self.loop = loop or asyncio.get_event_loop()
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.seq = 1
        self.is_connected = False
        
        # Parse channels
        initial_channels = self.api_config.get("zello_channels", [])
        if isinstance(initial_channels, str):
            initial_channels = [ch.strip() for ch in initial_channels.split(',') if ch.strip()]
        
        self.target_channels: List[str] = initial_channels or [self.api_config.get("zello_channel")]
        self.target_channels = [ch for ch in self.target_channels if ch]  # Filter empty
        
        self.last_channel_status: Dict[str, Any] = {}

        # Callbacks for event handling
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_event: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_audio_packet: Optional[Callable[[bytes], None]] = None
        self.on_channel_status_update: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_contacts_list: Optional[Callable[[Dict[str, Any]], None]] = None

    def generate_auth_token(self) -> Optional[str]:
        """
        Generates the JWT for production or returns a static token for development.
        """
        if self.api_config.get("auth_mode") == "production":
            logger.info("Generating production JWT...")
            try:
                private_key = self.api_config.get("private_key")
                issuer = self.api_config.get("issuer")

                if not private_key or not issuer:
                    error_msg = "JWT generation failed: private_key or issuer missing from config."
                    logger.critical(error_msg)
                    if self.on_error:
                        self.on_error(error_msg)
                    return None

                expiry = int(time.time()) + 3600
                token = jwt.encode({'iss': issuer, 'exp': expiry}, private_key, algorithm='RS256')
                logger.info("Production JWT generated successfully.")

                if self.on_event:
                    self.on_event({"command": "token_expiry_update", "expiry": expiry})
                return token
            except Exception as e:
                error_msg = f"Could not generate production JWT: {e}"
                logger.critical(f"{error_msg}\n{traceback.format_exc()}")
                if self.on_error:
                    self.on_error(error_msg)
                return None
        else:
            logger.info("Using static development token or password.")
            return self.api_config.get("auth_token") or self.api_config.get("zello_password")

    async def connect(self) -> None:
        """
        Establishes and maintains the connection to Zello, with automatic reconnection.
        """
        while True:
            try:
                auth_token = self.generate_auth_token()
                if not auth_token:
                    logger.warning("Auth token missing, retrying in 30s...")
                    await asyncio.sleep(30)
                    continue

                logger.info("Connecting to wss://zello.io/ws...")
                async with websockets.connect(
                    "wss://zello.io/ws",
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    self.websocket = websocket
                    self.is_connected = True
                    logger.info("WebSocket connection established. Authenticating with Zello...")

                    logon_payload = {
                        "command": "logon", 
                        "seq": self.seq, 
                        "auth_token": auth_token,
                        "username": self.api_config.get("zello_username"),
                        "password": self.api_config.get("zello_password"),
                        "channels": []
                    }
                    await self.send_json(logon_payload)

                    response = json.loads(await websocket.recv())
                    logger.debug(f"Received logon response: {response}")

                    if not response.get("success"):
                        error_msg = f"Authentication failed: {response.get('error')}."
                        logger.critical(error_msg)
                        if self.on_error: 
                            self.on_error(error_msg)
                        await asyncio.sleep(30)
                        continue

                    logger.info("Authentication successful.")
                    if self.on_connect: 
                        self.on_connect()
                    
                    if self.target_channels:
                        logger.info(f"Subscribing to channels: {self.target_channels}")
                        for channel in self.target_channels:
                            await self.send_json({"command": "start_channel_stream", "channel": channel})
                            await self.send_json({"command": "get_channel_status", "channel": channel})

                    await self.get_contacts()
                    await self._listen_for_messages()

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}. Reconnecting in 10s...")
            except Exception as e:
                logger.error(f"Unexpected connection error: {e}\n{traceback.format_exc()}")
                if self.on_error: 
                    self.on_error(str(e))
            finally:
                self.is_connected = False
                if self.on_disconnect: 
                    self.on_disconnect()
                await asyncio.sleep(10)

    async def _listen_for_messages(self) -> None:
        """Main loop to listen for incoming messages."""
        logger.info("Listening for messages...")
        while self.is_connected and self.websocket:
            try:
                message = await self.websocket.recv()

                if isinstance(message, str):
                    msg_json = json.loads(message)
                    logger.debug(f"Received JSON: {msg_json.get('command', 'N/A')}")
                    
                    if msg_json.get("command") == "on_channel_status":
                        channel_name = msg_json.get("channel")
                        if channel_name:
                            self.last_channel_status[channel_name] = msg_json
                        if self.on_channel_status_update:
                            self.on_channel_status_update(msg_json)
                    elif msg_json.get("command") == "on_users_list":
                        if self.on_contacts_list:
                            self.on_contacts_list(msg_json)
                    elif self.on_event:
                        self.on_event(msg_json)

                elif isinstance(message, bytes):
                    if self.on_audio_packet: 
                        self.on_audio_packet(message)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Listen loop detected connection closed.")
                break
            except Exception as e:
                logger.error(f"Error in message listener: {e}\n{traceback.format_exc()}")
                if self.on_error: 
                    self.on_error(f"Listener error: {e}")

    async def send_json(self, data: Dict[str, Any]) -> None:
        """Sends a JSON payload to the WebSocket."""
        if self.websocket and self.is_connected:
            self.seq += 1
            data['seq'] = self.seq
            await self.websocket.send(json.dumps(data))
        else:
            logger.warning("Cannot send JSON, not connected.")

    async def get_contacts(self) -> None:
        """Requests the user's contact list from Zello."""
        logger.info("Requesting contacts list...")
        await self.send_json({"command": "get_users_list"})

    async def disconnect(self) -> None:
        """Gracefully disconnects the client."""
        logger.info("Disconnecting...")
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info("Disconnected.")

    async def send_text_message(self, text: str, channel: str) -> None:
        """Sends a text message to a specific channel."""
        payload = {"command": "send_text_message", "channel": channel, "text": text}
        await self.send_json(payload)

    async def send_private_message(self, text: str, username: str) -> None:
        """Sends a private text message to a user."""
        payload = {"command": "send_text_message", "for": username, "text": text}
        await self.send_json(payload)

    async def update_channels(self, new_channel_list: List[str]) -> None:
        """Updates the monitored channels by triggering a full reconnect."""
        logger.info(f"Updating monitored channels to: {new_channel_list}")
        self.target_channels = new_channel_list
        self.last_channel_status = {}
        if self.websocket and self.is_connected:
            await self.disconnect()
        else:
            logger.info("Not currently connected. New channels will be used on next connection attempt.")
            
    async def set_status(self, status: str, channel: str) -> None:
        """Sets the user's status on a given channel."""
        logger.info(f"Setting status to {status} on channel {channel}")
        payload = {
            "command": "set_channel_status",
            "channel": channel,
            "status": status
        }
        await self.send_json(payload)
        await self.send_json({"command": "get_channel_status", "channel": channel})
