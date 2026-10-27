import re
import time
from .interfaces import ModelClient, CodeExecutor
from .models import Attempt, ExecutionResult, Problem, SolveResult, Status


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

    def solve(self, problem: Problem) -> SolveResult:
        attempts: list[Attempt] = []
        feedback = None
        for _ in range(self.max_attempts):
            started = time.monotonic()
            code = ''
            try:
                code = self.client.generate(problem, feedback)
                result = self.executor.run(problem, code)
            except Exception:
                result = ExecutionResult(Status.ERROR, 0, 'Model or executor error')
            attempts.append(Attempt(problem.id, code, result.status, time.monotonic() - started, result.error_summary))
            if result.status in (Status.PASSED, Status.UNAVAILABLE):
                break
            feedback = safe_feedback(result)
        return SolveResult(problem.id, attempts)
