"""Builder agent placeholder module."""
from __future__ import annotations


class BuilderAgent:
    """Stub implementation of the builder agent."""

    def run(self, plan: str) -> str:
        """Return a canned draft for testing purposes."""

        return f"Draft based on: {plan}"
"""Builder agent placeholder implementation."""


def build_draft(plan: list[str]) -> str:
    """Return a draft response given the plan."""

    return "\n".join(plan)
