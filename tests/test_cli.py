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
