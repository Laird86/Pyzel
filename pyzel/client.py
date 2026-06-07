import json
import time
import asyncio
import logging
import traceback
import inspect
from typing import Dict, List, Optional, Callable, Any, Union

import websockets
import jwt

logger = logging.getLogger(__name__)

class ZelloClient:
    """
    A modern, asynchronous Python SDK for the Zello Channel WebSocket API.
    Manages the WebSocket connection, authentication, and event handling.
    """
    def __init__(self, api_config: Dict[str, Any], loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Initializes the ZelloClient.

        Args:
            api_config (dict): Configuration dictionary containing credentials and settings.
            loop (asyncio.AbstractEventLoop, optional): The asyncio event loop. Defaults to None.
        """
        self.api_config = api_config
        
        if loop is None:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    self.loop = asyncio.get_event_loop()
                except RuntimeError:
                    self.loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.loop)
        else:
            self.loop = loop
            
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.seq = 1
        self.is_connected = False
        self._maintenance_task: Optional[asyncio.Task] = None
        
        # Parse channels
        initial_channels: List[str] = []
        raw_channels = self.api_config.get("zello_channels", [])
        if isinstance(raw_channels, str):
            initial_channels = [ch.strip() for ch in raw_channels.split(',') if ch.strip()]
        elif isinstance(raw_channels, list):
            initial_channels = [str(ch).strip() for ch in raw_channels if ch]
            
        fallback_channel = self.api_config.get("zello_channel")
        if not initial_channels and fallback_channel:
            initial_channels = [str(fallback_channel)]
            
        self.target_channels: List[str] = [ch for ch in initial_channels if ch]  # Filter empty
        
        self.last_channel_status: Dict[str, Any] = {}

        # Event dispatcher registry
        self._event_handlers: Dict[str, List[Callable]] = {}

    def on(self, event_name: str):
        """
        Decorator to register an event handler.
        
        Example:
            @client.on("on_text_message")
            async def handle_message(data):
                print(data["text"])
        """
        def decorator(func: Callable):
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            self._event_handlers[event_name].append(func)
            return func
        return decorator

    async def _emit(self, event_name: str, *args, **kwargs):
        """Dispatches an event to all registered handlers."""
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler(*args, **kwargs)
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler '{event_name}': {e}")
                    logger.debug(traceback.format_exc())

    def generate_auth_token(self) -> Optional[str]:
        """Generates the JWT for production or returns a static token for development."""
        if self.api_config.get("auth_mode") == "production":
            logger.info("Generating production JWT...")
            try:
                private_key = self.api_config.get("private_key")
                issuer = self.api_config.get("issuer")

                if not private_key or not issuer:
                    logger.critical("JWT generation failed: private_key or issuer missing from config.")
                    return None

                expiry = int(time.time()) + 3600
                token = jwt.encode({'iss': issuer, 'exp': expiry}, private_key, algorithm='RS256')
                
                # We can't await a sync method easily, so we rely on the loop for token updates later if needed.
                return token
            except Exception as e:
                logger.critical(f"Could not generate production JWT: {e}\n{traceback.format_exc()}")
                return None
        else:
            logger.info("Using static development token or password.")
            return self.api_config.get("auth_token") or self.api_config.get("zello_password")

    async def start(self) -> None:
        """
        Establishes and maintains the connection to Zello, with automatic reconnection.
        Should run as a background task.
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
                    logger.info("WebSocket connection established. Authenticating...")

                    logon_payload = {
                        "command": "logon", 
                        "seq": self.seq, 
                        "auth_token": auth_token,
                        "username": self.api_config.get("zello_username"),
                        "password": self.api_config.get("zello_password"),
                        "channels": self.target_channels
                    }
                    await self.send_json(logon_payload)

                    response = json.loads(await websocket.recv())
                    logger.debug(f"Received logon response: {response}")

                    if not response.get("success"):
                        error_msg = f"Authentication failed: {response.get('error')}."
                        logger.critical(error_msg)
                        await self._emit("error", error_msg)
                        await asyncio.sleep(30)
                        continue

                    logger.info("Authentication successful.")
                    await self._emit("connect")
                    
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
                logger.error(f"Unexpected connection error: {e}")
                await self._emit("error", str(e))
            finally:
                self.is_connected = False
                await self._emit("disconnect")
                await asyncio.sleep(10)

    async def _listen_for_messages(self) -> None:
        """Main loop to listen for incoming messages."""
        logger.info("Listening for messages...")
        while self.is_connected and self.websocket:
            try:
                message = await self.websocket.recv()

                if isinstance(message, str):
                    msg_json = json.loads(message)
                    command = msg_json.get("command", "unknown")
                    logger.debug(f"Received JSON: {command}")
                    
                    # Update local state cache if applicable
                    if command == "on_channel_status":
                        channel_name = msg_json.get("channel")
                        if channel_name:
                            self.last_channel_status[channel_name] = msg_json
                            
                    # Dispatch to strictly named handlers
                    await self._emit(command, msg_json)
                    # Dispatch a wildcard event
                    await self._emit("any_event", msg_json)

                elif isinstance(message, bytes):
                    # Dispatch binary audio streams
                    await self._emit("audio_packet", message)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Listen loop detected connection closed.")
                break
            except Exception as e:
                logger.error(f"Error in message listener: {e}\n{traceback.format_exc()}")
                await self._emit("error", str(e))

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
        await self.send_json({"command": "get_users_list"})

    async def disconnect(self) -> None:
        """Gracefully disconnects the client."""
        logger.info("Disconnecting...")
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        if self._maintenance_task:
            self._maintenance_task.cancel()
        logger.info("Disconnected.")

    async def send_text_message(self, text: str, channel: str) -> None:
        """Sends a text message to a specific channel."""
        payload = {"command": "send_text_message", "channel": channel, "text": text}
        await self.send_json(payload)

    async def send_private_message(self, text: str, username: str) -> None:
        """Sends a private text message to a user."""
        payload = {"command": "send_text_message", "for": username, "text": text}
        await self.send_json(payload)
        
    async def set_status(self, status: str, channel: str) -> None:
        """Sets the user's status on a given channel."""
        payload = {"command": "set_channel_status", "channel": channel, "status": status}
        await self.send_json(payload)
        await self.send_json({"command": "get_channel_status", "channel": channel})

    # -----------------------------------------------------
    # Async Context Manager Support (async with ZelloClient)
    # -----------------------------------------------------
    async def __aenter__(self):
        self._maintenance_task = self.loop.create_task(self.start())
        # Yield execution until connected (with timeout)
        for _ in range(50):
            if self.is_connected:
                break
            await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
