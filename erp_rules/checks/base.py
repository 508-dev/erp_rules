from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

WARN = "warn"  # shown to the user; the save goes ahead
BLOCK = "block"  # the save is stopped until the problem is fixed


@dataclass
class Problem:
    severity: str
    message: str


class BaseCheck(ABC):
    """Inspects a document and reports problems. Unlike a rule, a check never changes the document."""

    @abstractmethod
    def applies_to(self, doc: Any) -> bool:
        ...

    @abstractmethod
    def problems(self, doc: Any) -> list[Problem]:
        ...


def money(amount) -> str:
    return f"${float(amount or 0):,.2f}"
