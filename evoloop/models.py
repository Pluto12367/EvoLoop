from dataclasses import dataclass
from enum import StrEnum
from typing import Any
import keyword
from typing import Literal

FailureKind = Literal['solution', 'model', 'infrastructure', 'budget']


class BudgetExhausted(Exception):
    pass


@dataclass(frozen=True)
class TaskSpec:
    id: str
    description: str
    function_name: str


@dataclass(frozen=True)
class TestCase:
    __test__ = False
    args: list[Any]
    expected: Any


@dataclass(frozen=True)
class Problem:
    id: str
    description: str
    function_name: str
    tests: list[TestCase]

    def __post_init__(self) -> None:
        if not self.id or not self.function_name.isidentifier() or keyword.iskeyword(self.function_name):
            raise ValueError('Invalid problem ID or function name')


class Status(StrEnum):
    PASSED = 'passed'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    ERROR = 'error'
    UNAVAILABLE = 'unavailable'


@dataclass(frozen=True)
class ExecutionResult:
    status: Status
    elapsed_seconds: float
    error_summary: str | None = None
    failure_kind: FailureKind | None = None


@dataclass(frozen=True)
class Attempt:
    problem_id: str
    code: str
    test_result: Status
    elapsed_seconds: float
    error_summary: str | None
    failure_kind: FailureKind | None = None


@dataclass(frozen=True)
class SolveResult:
    problem_id: str
    attempts: list[Attempt]
