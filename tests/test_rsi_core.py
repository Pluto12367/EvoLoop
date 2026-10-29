import pytest
from evoloop.strategy import Strategy, MockStrategyProposer, MockStrategyClient
from evoloop.benchmark import Benchmark, demo_benchmark
from evoloop.evaluation import CallBudget, Evaluator
from evoloop.models import BudgetExhausted, ExecutionResult, Status


def test_strategy_versions_and_validation():
    a = Strategy.create('baseline')
    assert a.id == Strategy.create('baseline').id
    assert Strategy.create('improved', a.id).parent_id == a.id
    for text in (' ', 'x' * 4001):
        with pytest.raises(ValueError): Strategy.create(text)


def test_benchmark_rejects_overlap_and_snapshots():
    benchmark = demo_benchmark()
    with pytest.raises(ValueError): Benchmark('bad', benchmark.development, benchmark.development)
    tasks = benchmark.development
    original = benchmark.fingerprint
    tasks[0].tests.clear()
    assert benchmark.development[0].tests
    assert benchmark.fingerprint == original


def test_budget_has_hard_limit():
    budget = CallBudget(1)
    budget.consume()
    with pytest.raises(BudgetExhausted): budget.consume()
    assert budget.used == 1


def test_evaluator_preserves_partial_attempts_on_budget_exhaustion():
    class Executor:
        def run(self, problem, code): return ExecutionResult(Status.FAILED, 0, 'case 1 failed')
    budget = CallBudget(1)
    evaluation = Evaluator(MockStrategyClient(), Executor(), budget).evaluate(demo_benchmark().development, Strategy.create('baseline'))
    assert not evaluation.complete
    assert evaluation.failure_kind == 'budget'
    assert len(evaluation.results[0].attempts) == 2
    assert evaluation.calls == 1


def test_benchmark_rejects_empty_tests():
    from evoloop.models import Problem
    with pytest.raises(ValueError):
        Benchmark('bad', [Problem('empty', 'x', 'f', [])], demo_benchmark().holdout)


def test_strategy_prompt_contains_only_explicit_development_feedback():
    from evoloop.strategy import ModelStrategyProposer, DevelopmentFeedback
    from evoloop.models import TaskSpec
    class Client:
        prompt = None
        def complete(self, prompt):
            self.prompt = prompt
            return 'Review edge cases'
    client = Client()
    text = ModelStrategyProposer(client).propose(Strategy.create('baseline'), (DevelopmentFeedback(TaskSpec('public', 'description', 'f'), False, 'failed'),))
    assert text == 'Review edge cases'
    assert 'public' in client.prompt and 'description' in client.prompt
    assert 'expected' not in client.prompt
