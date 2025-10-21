"""Reviewer agent placeholder module."""
from __future__ import annotations


class ReviewerAgent:
    """Stub implementation of the reviewer agent."""

    def run(self, draft: str) -> str:
        """Return a canned review for testing purposes."""

        return f"Review of: {draft}"
"""Reviewer agent placeholder implementation."""


def review_draft(draft: str) -> str:
    """Return feedback for the provided draft."""

    return f"Looks good: {draft[:50]}..."
