import re
import time
from copy import deepcopy
from .interfaces import ModelClient, CodeExecutor
from .models import Attempt, BudgetExhausted, ExecutionResult, Problem, SolveResult, Status, TaskSpec


def safe_feedback(result: ExecutionResult) -> str:
    summary = result.error_summary or ''
    if re.fullmatch(r'case [1-9][0-9]* failed', summary):
        return summary
    return {'timeout': 'Execution timed out', 'failed': 'A test failed',
            'error': 'Code raised an exception', 'unavailable': 'Execution environment unavailable'}.get(result.status, 'Execution failed')


class Agent:
    def __init__(self, client: ModelClient, executor: CodeExecutor, max_attempts: int = 3):
        if not 1 <= max_attempts <= 3:
            raise ValueError('max_attempts must be between 1 and 3')
        self.client, self.executor, self.max_attempts = client, executor, max_attempts

    def solve(self, problem: Problem, strategy: str | None = None) -> SolveResult:
        attempts: list[Attempt] = []
        feedback = None
        for _ in range(self.max_attempts):
            started = time.monotonic()
            code = ''
            try:
                task = TaskSpec(problem.id, problem.description, problem.function_name)
                code = (self.client.generate(task, feedback) if strategy is None else
                        self.client.generate(task, feedback, strategy=strategy))
            except BudgetExhausted:
                result = ExecutionResult(Status.ERROR, 0, 'Model call budget exhausted', 'budget')
            except Exception:
                result = ExecutionResult(Status.ERROR, 0, 'Model request failed', 'model')
            else:
                try:
                    result = self.executor.run(deepcopy(problem), code)
                except Exception:
                    result = ExecutionResult(Status.ERROR, 0, 'Executor failed', 'infrastructure')
            kind = result.failure_kind
            if result.status == Status.UNAVAILABLE:
                kind = 'infrastructure'
            if kind is None and result.status != Status.PASSED:
                kind = 'solution'
            summary = None
            if result.status != Status.PASSED:
                summary = {'model': 'Model request failed', 'infrastructure': 'Execution environment unavailable',
                           'budget': 'Model call budget exhausted'}.get(kind, safe_feedback(result))
            attempts.append(Attempt(problem.id, code, result.status, time.monotonic() - started, summary, kind))
            if result.status in (Status.PASSED, Status.UNAVAILABLE) or kind in ('model', 'infrastructure', 'budget'):
                break
            feedback = safe_feedback(result)
        return SolveResult(problem.id, attempts)
