from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from .auth import (
    build_logon_payload,
    build_ping_payload,
    build_text_message_payload,
    create_production_auth_token,
)
from .exceptions import AuthenticationError, ChannelError, PyzelConnectionIssue

EventCallback = Callable[[dict[str, Any]], None | Awaitable[None]]
ErrorCallback = Callable[[Exception], None | Awaitable[None]]
SocketFactory = Callable[[str], Any | Awaitable[Any]]


class ZelloClient:
    """Small async client for the Zello Channel API.

    By default, ``connect()`` uses safe offline mode: it marks the client as
    connected and returns payloads without contacting Zello. Passing
    ``open_socket=True`` opens a real WebSocket connection. Tests can inject a
    fake socket factory so CI never needs live Zello credentials.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        auth_token: str | None = None,
        refresh_token: str | None = None,
        issuer: str | None = None,
        signing_key: str | None = None,
        endpoint: str = "wss://zello.io/ws",
        channel: str | None = None,
        channels: Sequence[str] | None = None,
        socket_factory: SocketFactory | None = None,
    ):
        self.username = username
        self.password = password
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.issuer = issuer
        self.signing_key = signing_key
        self.endpoint = endpoint
        self.connected = False
        self.channel = channel
        self.channels = list(channels or [])
        self.websocket: Any | None = None
        self.socket_factory = socket_factory
        self.seq = 0
        self.on_event: EventCallback | None = None
        self.on_error: ErrorCallback | None = None
        self.auth_token_expires_at: int | None = None

    def set_event_callback(self, callback: EventCallback | None) -> None:
        self.on_event = callback

    def set_error_callback(self, callback: ErrorCallback | None) -> None:
        self.on_error = callback

    async def _emit_event(self, event: dict[str, Any]) -> None:
        if not self.on_event:
            return
        result = self.on_event(event)
        if hasattr(result, "__await__"):
            await result

    async def _emit_error(self, error: Exception) -> None:
        if not self.on_error:
            return
        result = self.on_error(error)
        if hasattr(result, "__await__"):
            await result

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def _get_auth_token(self) -> str | None:
        if self.auth_token:
            return self.auth_token
        if self.issuer and self.signing_key:
            token, expires_at = create_production_auth_token(
                issuer=self.issuer,
                signing_key=self.signing_key,
            )
            self.auth_token = token
            self.auth_token_expires_at = expires_at
            return token
        return None

    async def _open_websocket(self) -> Any:
        if self.socket_factory is not None:
            socket = self.socket_factory(self.endpoint)
            if hasattr(socket, "__await__"):
                socket = await socket
            return socket

        try:
            import websockets
        except Exception as exc:  # pragma: no cover - dependency guard
            raise PyzelConnectionIssue("websockets is required for live connections") from exc

        return await websockets.connect(self.endpoint, subprotocols=["zello"])

    async def connect(self, *, open_socket: bool = False) -> bool:
        """Connect the client.

        ``open_socket=False`` keeps tests and examples offline. Use
        ``open_socket=True`` for a live WebSocket connection.
        """

        if open_socket:
            self.websocket = await self._open_websocket()
        self.connected = True
        return True

    async def disconnect(self) -> bool:
        self.connected = False
        self.channel = None
        if self.websocket is not None:
            close = getattr(self.websocket, "close", None)
            if callable(close):
                result = close()
                if hasattr(result, "__await__"):
                    await result
            self.websocket = None
        return True

    async def send_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.connected:
            raise PyzelConnectionIssue("client is not connected")

        outgoing = dict(payload)
        outgoing["seq"] = self._next_seq()

        if self.websocket is not None:
            send = getattr(self.websocket, "send", None)
            if not callable(send):
                raise PyzelConnectionIssue("websocket object does not support send")
            result = send(json.dumps(outgoing))
            if hasattr(result, "__await__"):
                await result

        return outgoing

    async def receive(self) -> dict[str, Any] | bytes:
        if not self.connected or self.websocket is None:
            raise PyzelConnectionIssue("client is not connected to a websocket")

        recv = getattr(self.websocket, "recv", None)
        if not callable(recv):
            raise PyzelConnectionIssue("websocket object does not support recv")

        message = recv()
        if hasattr(message, "__await__"):
            message = await message
        return await self.handle_message(message)

    async def join_channel(self, channel: str | None = None) -> dict[str, Any]:
        if not self.connected:
            raise PyzelConnectionIssue("client must connect before joining a channel")

        target_channel = channel or self.channel
        payload = build_logon_payload(
            channel=target_channel,
            channels=self.channels,
            username=self.username,
            password=self.password,
            auth_token=self._get_auth_token(),
            refresh_token=self.refresh_token,
        )
        if target_channel:
            self.channel = target_channel.strip()
        return await self.send_json(payload)

    async def send_text_message(self, text: str, channel: str | None = None) -> dict[str, Any]:
        target_channel = channel or self.channel
        if not target_channel:
            raise ChannelError("channel is required")
        payload = build_text_message_payload(text=text, channel=target_channel)
        return await self.send_json(payload)

    async def ping(self) -> dict[str, Any]:
        return await self.send_json(build_ping_payload())

    async def handle_message(self, message: str | bytes) -> dict[str, Any] | bytes:
        """Parse one incoming websocket message and dispatch callbacks."""

        if isinstance(message, bytes):
            return message

        try:
            payload = json.loads(message)
        except json.JSONDecodeError as exc:
            await self._emit_error(exc)
            raise

        if not isinstance(payload, dict):
            error = ValueError("websocket text message was not a JSON object")
            await self._emit_error(error)
            raise error

        await self._emit_event(payload)
        return payload
