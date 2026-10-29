import pytest
from evoloop.executor import DockerExecutor
from evoloop.models import Problem, TestCase, Status


pytestmark = pytest.mark.integration


@pytest.mark.parametrize(('code', 'expected'), [
    ('def f(x): return x + 1', Status.PASSED),
    ('def f(x): return 0', Status.FAILED),
    ('def f(x): raise ValueError()', Status.ERROR),
    ('def f(x):\n    while True: pass', Status.TIMEOUT),
])
def test_real_container(code, expected):
    problem = Problem('p', 'increment', 'f', [TestCase([1], 2)])
    assert DockerExecutor(timeout=5).run(problem, code).status == expected


def test_real_mock_strategy_improvement(tmp_path, capsys):
    import json
    from evoloop.cli import main
    assert main(['--improve', '--state-dir', str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['baseline_development']['pass_rate'] == 0
    assert report['rounds'][0]['evaluation']['pass_rate'] == 1
    assert report['holdout_candidate']['pass_rate'] == 1
    assert report['promotion_eligible'] and report['persisted']
    active = json.loads((tmp_path / 'active_strategy.json').read_text())
    assert active['id'] == report['selected_strategy']['id']


def test_process_exit_can_retry_in_real_docker():
    from evoloop.agent import Agent
    class Client:
        calls = 0
        def generate(self, task, feedback):
            self.calls += 1
            return 'import os; os._exit(1)' if self.calls == 1 else 'def f(): return 1'
    client = Client()
    result = Agent(client, DockerExecutor()).solve(Problem('exit', 'Return one', 'f', [TestCase([], 1)]))
    assert len(result.attempts) == 2
    assert result.attempts[0].failure_kind == 'solution'
    assert result.attempts[-1].test_result == Status.PASSED
