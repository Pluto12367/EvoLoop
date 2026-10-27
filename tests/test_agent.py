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
