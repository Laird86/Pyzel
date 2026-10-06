from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    """A Zello channel reference."""

    name: str


@dataclass(frozen=True)
class User:
    """A Zello user reference."""

    username: str
    display_name: str | None = None


@dataclass(frozen=True)
class TextMessage:
    """A text message received from or sent to a channel."""

    sender: str
    text: str
    channel: str | None = None
