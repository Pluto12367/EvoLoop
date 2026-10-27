import subprocess
from unittest.mock import patch
from evoloop.executor import DockerExecutor
from evoloop.models import Problem, TestCase, Status


def test_docker_missing_fails_closed():
    with patch('evoloop.executor.subprocess.run', side_effect=FileNotFoundError):
        result = DockerExecutor().run(Problem('p', 'x', 'f', [TestCase([], 1)]), 'def f(): return 1')
    assert result.status == Status.UNAVAILABLE


def test_timeout_stops_container():
    with patch('evoloop.executor.subprocess.run', side_effect=[subprocess.TimeoutExpired('docker', 1), subprocess.CompletedProcess([], 0)]) as run:
        result = DockerExecutor(timeout=1).run(Problem('p', 'x', 'f', []), 'while True: pass')
    assert result.status == Status.TIMEOUT
    assert run.call_args_list[1].args[0][1:3] == ['rm', '-f']


def test_safe_docker_flags_and_pass_result():
    with patch('evoloop.executor.subprocess.run', return_value=subprocess.CompletedProcess([], 0, stdout='EVOL_RESULT:passed:0\n', stderr='')) as run:
        result = DockerExecutor().run(Problem('p', 'x', 'f', [TestCase([], 1)]), 'def f(): return 1')
    cmd = run.call_args.args[0]
    assert result.status == Status.PASSED
    assert '--read-only' in cmd and '--network=none' in cmd and '--cap-drop=ALL' in cmd
    assert '--mount' not in cmd and '-v' not in cmd


def test_bad_result_does_not_leak_container_output():
    with patch('evoloop.executor.subprocess.run', return_value=subprocess.CompletedProcess([], 0, stdout='secret', stderr='secret')):
        result = DockerExecutor().run(Problem('p', 'x', 'f', []), 'pass')
    assert result.status == Status.ERROR
    assert 'secret' not in result.error_summary


def test_docker_connection_error_is_unavailable():
    with patch('evoloop.executor.subprocess.run', return_value=subprocess.CompletedProcess([], 1, stdout='', stderr='failed to connect to the docker API')):
        result = DockerExecutor().run(Problem('p', 'x', 'f', []), 'pass')
    assert result.status == Status.UNAVAILABLE
