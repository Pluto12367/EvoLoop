import json
from unittest.mock import patch
from evoloop.cli import main
from evoloop.models import ExecutionResult, Status
from evoloop.clients import MockModelClient, OpenAICompatibleClient
from evoloop.examples import example_problems


def test_mock_model_generates_code_for_examples():
    for problem in example_problems():
        assert 'def ' + problem.function_name in MockModelClient().generate(problem, None)


def test_cli_outputs_complete_json_report(capsys):
    with patch('evoloop.cli.DockerExecutor.run', return_value=ExecutionResult(Status.PASSED, 0.1)):
        assert main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert len(report['problems']) == 2
    assert all(item['attempts'][0]['test_result'] == 'passed' for item in report['problems'])
    assert all(item['attempts'][0]['code'] for item in report['problems'])


def test_cli_reports_unavailable_as_failure(capsys):
    with patch('evoloop.cli.DockerExecutor.run', return_value=ExecutionResult(Status.UNAVAILABLE, 0.1, 'Docker unavailable')):
        assert main([]) == 1
    assert json.loads(capsys.readouterr().out)['problems'][0]['attempts'][0]['test_result'] == 'unavailable'


def test_openai_client_sends_prompt_and_reads_code():
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"choices":[{"message":{"content":"def add(a, b): return a + b"}}]}'
    with patch('evoloop.clients.urlopen', return_value=Response()) as request:
        code = OpenAICompatibleClient('https://example.com/v1', 'key', 'model').generate(example_problems()[0], 'case 1 failed')
    assert code.startswith('def add')
    assert b'case 1 failed' in request.call_args.args[0].data


def test_cli_improvement_reports_and_reloads_strategy(tmp_path, capsys):
    from tests.test_improvement import FixtureExecutor
    with patch('evoloop.cli.DockerExecutor.run', new=FixtureExecutor().run):
        assert main(['--improve', '--state-dir', str(tmp_path)]) == 0
        first = json.loads(capsys.readouterr().out)
        assert first['promotion_eligible'] and first['persisted']
        assert main(['--improve', '--state-dir', str(tmp_path)]) == 0
        second = json.loads(capsys.readouterr().out)
    assert second['baseline_strategy']['id'] == first['selected_strategy']['id']
    assert second['stop_reason'] == 'no_improvement'


def test_cli_catalog_is_offline_and_lists_core(capsys):
    assert main(['--list-benchmarks']) == 0
    catalog = {b['name']: b for b in json.loads(capsys.readouterr().out)}
    assert catalog['core']['development'] == 16
    assert catalog['core']['holdout'] == 8


def test_canned_mock_cannot_score_core_benchmark(tmp_path):
    import pytest
    with pytest.raises(SystemExit) as error:
        main(['--improve', '--benchmark', 'core', '--state-dir', str(tmp_path)])
    assert error.value.code == 2
    assert not list(tmp_path.iterdir())


def test_cli_selects_core_for_real_client_without_network(tmp_path, capsys):
    class Client:
        def __init__(self, *args): pass
        def generate(self, problem, feedback, *, strategy=''):
            assert not hasattr(problem, 'tests')
            return 'pass'
        def complete(self, prompt): return 'Consider edge cases'
    with patch.dict('os.environ', {'EVOLOOP_API_KEY': 'test-key', 'EVOLOOP_BASE_URL': 'https://example.com/v1', 'EVOLOOP_MODEL': 'test-model'}):
        with patch('evoloop.cli.OpenAICompatibleClient', Client):
            with patch('evoloop.cli.DockerExecutor.run', return_value=ExecutionResult(Status.PASSED, 0)):
                assert main(['--improve', '--model', 'openai-compatible', '--benchmark', 'core', '--rounds', '1', '--state-dir', str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['benchmark']['id'] == 'python-core-v1'
    assert report['baseline_development']['total'] == 16
    assert report['stop_reason'] == 'no_improvement'
