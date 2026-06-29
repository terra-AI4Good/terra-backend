"""Evaluation framework base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from terra.agents.base import AgentResult


class EvalCase(BaseModel):
    """A single evaluation test case."""

    name: str
    input_message: str
    expected_output: str | None = None
    expected_tool_calls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalResult(BaseModel):
    """Result of evaluating an agent on a test case."""

    case_name: str
    passed: bool
    score: float = 0.0
    agent_result: AgentResult | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class EvalSuite(ABC):
    """Abstract base for evaluation suites.

    Implement this to define a set of test cases and scoring logic
    for agent behavior validation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the evaluation suite."""

    @abstractmethod
    def cases(self) -> list[EvalCase]:
        """Return the test cases for this suite."""

    @abstractmethod
    async def evaluate(
        self,
        case: EvalCase,
        result: AgentResult,
    ) -> EvalResult:
        """Score an agent's result against a test case.

        Args:
            case: The evaluation test case.
            result: The agent's actual output.

        Returns:
            EvalResult with pass/fail and score.
        """

    async def run_all(
        self,
        run_fn: Any,
    ) -> list[EvalResult]:
        """Run all cases through the provided execution function.

        Args:
            run_fn: Async callable(input_message) -> AgentResult

        Returns:
            List of evaluation results.
        """
        results: list[EvalResult] = []
        for case in self.cases():
            try:
                agent_result = await run_fn(case.input_message)
                eval_result = await self.evaluate(case, agent_result)
            except Exception as e:
                eval_result = EvalResult(
                    case_name=case.name,
                    passed=False,
                    error=str(e),
                )
            results.append(eval_result)
        return results
