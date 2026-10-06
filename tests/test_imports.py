import json

import pytest

from pyzel import (
    Channel,
    PyzelConnectionIssue,
    PyzelError,
    TextMessage,
    User,
    ZelloClient,
)
from pyzel.auth import build_logon_payload, build_ping_payload, build_text_message_payload


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.incoming = []

    async def send(self, message):
        self.sent.append(message)

    async def recv(self):
        return self.incoming.pop(0)

    async def close(self):
        self.closed = True


def test_public_imports():
    assert ZelloClient is not None
    assert Channel is not None
    assert User is not None
    assert TextMessage is not None
    assert issubclass(PyzelConnectionIssue, PyzelError)


def test_models():
    channel = Channel(name="ExampleChannel")
    user = User(username="example", display_name="Example User")
    message = TextMessage(sender="example", text="hello", channel="ExampleChannel")

    assert channel.name == "ExampleChannel"
    assert user.username == "example"
    assert user.display_name == "Example User"
    assert message.sender == "example"
    assert message.text == "hello"
    assert message.channel == "ExampleChannel"


def test_payload_helpers():
    assert build_logon_payload(
        channel="ExampleChannel",
        username="example",
        password="password",
    ) == {
        "command": "logon",
        "channels": ["ExampleChannel"],
        "username": "example",
        "password": "password",
    }
    assert build_text_message_payload(text="hello", channel="ExampleChannel") == {
        "command": "send_text_message",
        "channel": "ExampleChannel",
        "text": "hello",
    }
    assert build_ping_payload() == {"command": "ping"}


@pytest.mark.asyncio
async def test_connect_and_join_channel_payload():
    client = ZelloClient(username="example", password="example")

    assert client.connected is False

    connected = await client.connect()
    assert connected is True
    assert client.connected is True

    result = await client.join_channel("ExampleChannel")
    assert result == {
        "command": "logon",
        "channels": ["ExampleChannel"],
        "username": "example",
        "password": "example",
        "seq": 1,
    }
    assert client.channel == "ExampleChannel"


@pytest.mark.asyncio
async def test_send_text_message_payload():
    client = ZelloClient(username="example", password="example")
    await client.connect()
    await client.join_channel("ExampleChannel")

    result = await client.send_text_message("hello")
    assert result == {
        "command": "send_text_message",
        "channel": "ExampleChannel",
        "text": "hello",
        "seq": 2,
    }


@pytest.mark.asyncio
async def test_fake_websocket_send_and_receive():
    fake_socket = FakeWebSocket()
    fake_socket.incoming.append('{"command": "on_online", "success": true}')

    client = ZelloClient(
        username="example",
        password="example",
        socket_factory=lambda endpoint: fake_socket,
    )

    await client.connect(open_socket=True)
    assert client.connected is True
    assert client.websocket is fake_socket

    await client.join_channel("ExampleChannel")
    sent_payload = json.loads(fake_socket.sent[0])
    assert sent_payload["command"] == "logon"
    assert sent_payload["channels"] == ["ExampleChannel"]
    assert "channel" not in sent_payload
    assert sent_payload["seq"] == 1

    received = await client.receive()
    assert received == {"command": "on_online", "success": True}

    await client.disconnect()
    assert fake_socket.closed is True
    assert client.connected is False


@pytest.mark.asyncio
async def test_join_channel_requires_connection():
    client = ZelloClient(username="example", password="example")

    with pytest.raises(PyzelConnectionIssue):
        await client.join_channel("ExampleChannel")
