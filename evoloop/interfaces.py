from typing import Protocol
from .models import Problem, ExecutionResult


class ModelClient(Protocol):
    def generate(self, problem: Problem, feedback: str | None) -> str: ...


class CodeExecutor(Protocol):
    def run(self, problem: Problem, code: str) -> ExecutionResult: ...
