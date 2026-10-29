from dataclasses import dataclass
import time
from .agent import Agent
from .interfaces import ModelClient, CodeExecutor
from .models import BudgetExhausted, Problem, SolveResult, Status, TaskSpec
from .strategy import Strategy, DevelopmentFeedback


@dataclass
class CallBudget:
    limit: int = 100
    used: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.used != 0:
            raise ValueError('Call budget must start at zero with a positive limit')

    def consume(self) -> None:
        if self.used >= self.limit:
            raise BudgetExhausted()
        self.used += 1


class BudgetedClient:
    def __init__(self, client: ModelClient, budget: CallBudget):
        self.client, self.budget = client, budget

    def generate(self, problem: TaskSpec, feedback: str | None, *, strategy: str = '') -> str:
        self.budget.consume()
        return self.client.generate(problem, feedback, strategy=strategy)


@dataclass(frozen=True)
class Evaluation:
    results: list[SolveResult]
    total: int
    passed: int
    pass_rate: float
    first_attempt_rate: float
    attempts: int
    calls: int
    elapsed_seconds: float
    complete: bool
    failure_kind: str | None

    def feedback(self, problems: list[Problem]) -> tuple[DevelopmentFeedback, ...]:
        public = {p.id: TaskSpec(p.id, p.description, p.function_name) for p in problems}
        return tuple(DevelopmentFeedback(public[r.problem_id], r.attempts[-1].test_result == Status.PASSED,
                                         None if r.attempts[-1].test_result == Status.PASSED else r.attempts[-1].test_result.value)
                     for r in self.results)


class Evaluator:
    def __init__(self, client: ModelClient, executor: CodeExecutor, budget: CallBudget, max_attempts: int = 3):
        self.budget = budget
        self.agent = Agent(BudgetedClient(client, budget), executor, max_attempts)

    def evaluate(self, problems: list[Problem], strategy: Strategy) -> Evaluation:
        start, before = time.monotonic(), self.budget.used
        results: list[SolveResult] = []
        failure = None
        for problem in problems:
            result = self.agent.solve(problem, strategy.text)
            results.append(result)
            kind = result.attempts[-1].failure_kind
            if kind in ('model', 'infrastructure', 'budget'):
                failure = kind
                break
        passed = sum(r.attempts[-1].test_result == Status.PASSED for r in results)
        first = sum(r.attempts[0].test_result == Status.PASSED for r in results)
        return Evaluation(results, len(problems), passed, passed / len(problems), first / len(problems),
                          sum(len(r.attempts) for r in results), self.budget.used - before,
                          time.monotonic() - start, failure is None, failure)
