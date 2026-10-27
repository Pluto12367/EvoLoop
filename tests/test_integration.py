import subprocess
import pytest
from evoloop.executor import DockerExecutor
from evoloop.models import Problem, TestCase, Status


def docker_ready():
    try:
        return subprocess.run(['docker', 'image', 'inspect', 'python:3.12-alpine'], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not docker_ready(), reason='Docker daemon or python:3.12-alpine image unavailable')
@pytest.mark.parametrize(('code', 'expected'), [
    ('def f(x): return x + 1', Status.PASSED),
    ('def f(x): return 0', Status.FAILED),
    ('def f(x): raise ValueError()', Status.ERROR),
    ('def f(x):\n    while True: pass', Status.TIMEOUT),
])
def test_real_container(code, expected):
    problem = Problem('p', 'increment', 'f', [TestCase([1], 2)])
    assert DockerExecutor(timeout=5).run(problem, code).status == expected
