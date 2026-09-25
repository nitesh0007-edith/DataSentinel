"""Domain errors that the API layer maps to HTTP responses."""

from __future__ import annotations


class DataSentinelError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(DataSentinelError):
    status_code = 404


class ConflictError(DataSentinelError):
    """The requested action is not valid in the current workflow state."""

    status_code = 409


class UnsafeOperationError(DataSentinelError):
    status_code = 403
