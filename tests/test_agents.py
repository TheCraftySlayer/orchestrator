"""Smoke tests for agent stubs."""
from __future__ import annotations

from orchestrator.agents.builder import BuilderAgent
from orchestrator.agents.planner import PlanningAgent
from orchestrator.agents.researcher import ResearchAgent
from orchestrator.agents.reviewer import ReviewerAgent


def test_research_agent():
    agent = ResearchAgent()
    assert "Researching" in agent.run("topic")


def test_planning_agent():
    agent = PlanningAgent()
    assert "Plan" in agent.run("summary")


def test_builder_agent():
    agent = BuilderAgent()
    assert "Draft" in agent.run("plan")


def test_reviewer_agent():
    agent = ReviewerAgent()
    assert "Review" in agent.run("draft")
