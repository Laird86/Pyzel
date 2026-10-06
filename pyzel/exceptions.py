class PyzelError(Exception):
    """Base exception for Pyzel errors."""


class AuthenticationError(PyzelError):
    """Raised when authentication fails or auth data is invalid."""


class PyzelConnectionIssue(PyzelError):
    """Raised when a connection operation fails."""


class ChannelError(PyzelError):
    """Raised when a channel operation fails."""
