import pytest
from evoloop.models import Problem, TestCase, Status, ExecutionResult
from evoloop.agent import Agent


def problem():
    return Problem('sum', 'Add two integers', 'add', [TestCase([1, 2], 3)])


def test_problem_validates_function_name():
    with pytest.raises(ValueError):
        Problem('x', 'description', 'bad-name', [])


def test_agent_retries_with_safe_feedback_and_stops_after_three():
    class Client:
        def __init__(self): self.feedback = []
        def generate(self, problem, feedback):
            self.feedback.append(feedback)
            return 'def add(a, b): return 0'
    class Executor:
        def run(self, problem, code):
            return ExecutionResult(Status.FAILED, 0.1, 'case 1 failed')
    client = Client()
    result = Agent(client, Executor()).solve(problem())
    assert len(result.attempts) == 3
    assert client.feedback == [None, 'case 1 failed', 'case 1 failed']
    assert all(a.problem_id == 'sum' for a in result.attempts)


def test_agent_stops_after_success():
    class Client:
        def generate(self, problem, feedback): return 'def add(a, b): return a + b'
    class Executor:
        def run(self, problem, code): return ExecutionResult(Status.PASSED, 0.1, None)
    assert len(Agent(Client(), Executor()).solve(problem()).attempts) == 1


def test_model_receives_only_public_task_view():
    class Client:
        def generate(self, task, feedback):
            assert not hasattr(task, 'tests')
            return 'def add(a,b): return a+b'
    class Executor:
        def run(self, problem, code): return ExecutionResult(Status.PASSED, 0)
    assert Agent(Client(), Executor()).solve(problem()).attempts[-1].test_result == Status.PASSED


def test_model_error_is_infrastructure_and_stops():
    class Client:
        def generate(self, task, feedback): raise RuntimeError('secret')
    result = Agent(Client(), None).solve(problem())
    assert len(result.attempts) == 1
    assert result.attempts[0].failure_kind == 'model'
    assert 'secret' not in result.attempts[0].error_summary


def test_executor_exception_is_infrastructure_and_stops():
    class Client:
        def generate(self, task, feedback): return 'pass'
    class Executor:
        def run(self, problem, code): raise OSError('secret')
    result = Agent(Client(), Executor()).solve(problem())
    assert len(result.attempts) == 1
    assert result.attempts[0].failure_kind == 'infrastructure'


@pytest.mark.parametrize('kind', ['solution', 'infrastructure', 'model'])
def test_explicit_failure_kind_does_not_bypass_summary_filter(kind):
    class Client:
        def generate(self, task, feedback): return 'pass'
    class Executor:
        def run(self, problem, code):
            return ExecutionResult(Status.ERROR, 0, 'secret test input = [413]', kind)
    result = Agent(Client(), Executor()).solve(problem())
    assert all('secret' not in a.error_summary and '413' not in a.error_summary for a in result.attempts)


def test_executor_mutation_cannot_change_later_attempt_inputs():
    task = problem()
    class Client:
        def generate(self, task, feedback): return 'pass'
    class Executor:
        observed = []
        def run(self, problem, code):
            self.observed.append(list(problem.tests[0].args))
            problem.tests[0].args.clear()
            return ExecutionResult(Status.FAILED, 0, 'case 1 failed')
    executor = Executor()
    Agent(Client(), executor).solve(task)
    assert executor.observed == [[1, 2], [1, 2], [1, 2]]
    assert task.tests[0].args == [1, 2]
