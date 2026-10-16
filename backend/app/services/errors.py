"""Domain errors mapped to the API error shape in docs/API.md section 1."""
from __future__ import annotations


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details or {}


def bad_request(code: str, message: str, **details) -> DomainError:
    return DomainError(400, code, message, details)


def forbidden(code: str, message: str, **details) -> DomainError:
    return DomainError(403, code, message, details)


def not_found(what: str, ident) -> DomainError:
    return DomainError(404, "not_found", f"{what} {ident} not found")


def conflict(code: str, message: str, **details) -> DomainError:
    return DomainError(409, code, message, details)
