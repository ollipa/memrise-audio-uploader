"""Memrise SDK exceptions."""


class MemriseException(Exception):
    """Memrise SDK base exception."""


class AuthenticationError(MemriseException):
    """Memrise authentication failed."""


class MemriseConnectionError(MemriseException):
    """Connection to Memrise failed."""


class ParseError(MemriseException):
    """Parsing response from Memrise failed."""
