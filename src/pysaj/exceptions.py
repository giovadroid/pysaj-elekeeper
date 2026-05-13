"""Exceptions raised by PySaj."""

from __future__ import annotations

from typing import Any


class SajError(Exception):
    """Base exception for PySaj."""


class SajAuthError(SajError):
    """Raised when authentication fails or is required."""


class SajApiError(SajError):
    """Raised when the SAJ API returns a non-zero errCode."""

    def __init__(self, err_code: int | str, err_msg: str, payload: dict[str, Any] | None = None):
        super().__init__(f"SAJ API error {err_code}: {err_msg}")
        self.err_code = err_code
        self.err_msg = err_msg
        self.payload = payload or {}
