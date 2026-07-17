"""Provider-neutral AI interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AIResponse:
    """A normalized successful provider response."""

    content: str
    provider: str
    model_name: str


class AIProviderError(RuntimeError):
    """A safe AI error identified by a non-sensitive code."""

    def __init__(self, code: str) -> None:
        """Store only a safe error code."""

        super().__init__(code)
        self.code = code


class AIProvider(ABC):
    """Abstract interface implemented by every AI provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a short provider identifier."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured model name."""

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """Return whether the provider is local demonstration mode."""

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
    ) -> AIResponse:
        """Generate a text or JSON response from role-based messages."""
