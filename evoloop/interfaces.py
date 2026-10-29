from typing import Protocol
from .models import Problem, TaskSpec, ExecutionResult


class ModelClient(Protocol):
    def generate(self, problem: TaskSpec, feedback: str | None, *, strategy: str = '') -> str: ...


class CodeExecutor(Protocol):
    def run(self, problem: Problem, code: str) -> ExecutionResult: ...


class TextCompletionClient(Protocol):
    def complete(self, prompt: str) -> str: ...
