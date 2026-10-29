"""Trusted reference code validates the curated suite, never model-generated code."""
from copy import deepcopy
import inspect

import pytest

from evoloop.benchmark import load_benchmark
from evoloop.executor import DockerExecutor
from evoloop.models import Status
from reference_solutions import CORE_REFERENCES


TASKS = load_benchmark('core').development + load_benchmark('core').holdout


@pytest.mark.parametrize('problem', TASKS, ids=lambda p: p.id)
def test_trusted_reference_matches_all_expected_cases(problem):
    reference = CORE_REFERENCES[problem.function_name]
    for case in problem.tests:
        assert reference(*deepcopy(case.args)) == case.expected
    assert any(case.expected is not None for case in problem.tests), 'constant None must fail'


def test_reference_coverage_matches_suite_exactly():
    assert {p.function_name for p in TASKS} == set(CORE_REFERENCES)


@pytest.mark.integration
@pytest.mark.parametrize('problem', TASKS, ids=lambda p: p.id)
def test_core_reference_runs_in_real_docker(problem):
    code = inspect.getsource(CORE_REFERENCES[problem.function_name])
    result = DockerExecutor(timeout=10).run(problem, code)
    assert result.status == Status.PASSED, (problem.id, result)
