"""Behavioral checks for the Docker integration-test gate."""

from pathlib import Path
import subprocess

import pytest


pytest_plugins = ["pytester"]


class DockerProbe:
    """Replace only the external Docker CLI in a nested pytest run."""

    def __init__(self, unavailable=None):
        self.unavailable = unavailable
        self.patch = pytest.MonkeyPatch()

    def pytest_sessionstart(self, session):
        real_run = subprocess.run

        def run(command, *args, **kwargs):
            if command[0] != "docker":
                return real_run(command, *args, **kwargs)
            if self.unavailable == "missing-cli":
                raise FileNotFoundError("docker is not installed")
            if self.unavailable == "timeout":
                raise subprocess.TimeoutExpired(command, 5)
            if command == ["docker", "info"]:
                return subprocess.CompletedProcess(
                    command, int(self.unavailable == "daemon"), "", "daemon unavailable"
                )
            if command == ["docker", "image", "inspect", "python:3.12-alpine"]:
                return subprocess.CompletedProcess(
                    command, int(self.unavailable == "image"), "", "image unavailable"
                )
            raise AssertionError(f"Unexpected Docker command (tests must not pull): {command}")

        self.patch.setattr(subprocess, "run", run)

    def pytest_unconfigure(self, config):
        self.patch.undo()


def run_integration_session(pytester, monkeypatch, required, unavailable=None):
    if required:
        monkeypatch.setenv("EVOLOOP_REQUIRE_DOCKER", "1")
    else:
        monkeypatch.delenv("EVOLOOP_REQUIRE_DOCKER", raising=False)
    policy = Path(__file__).with_name("conftest.py")
    pytester.makeconftest(policy.read_text(encoding="utf-8") if policy.exists() else "")
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.integration
        def test_container():
            assert True

        def test_unit():
            assert True
        """
    )
    return pytester.runpytest_inprocess("-q", plugins=[DockerProbe(unavailable)])


@pytest.mark.parametrize("required", [False, True])
def test_available_docker_runs_integration(pytester, monkeypatch, required):
    result = run_integration_session(pytester, monkeypatch, required)
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize("unavailable", ["missing-cli", "daemon", "image", "timeout"])
def test_local_unavailable_docker_skips_integration(pytester, monkeypatch, unavailable):
    result = run_integration_session(pytester, monkeypatch, False, unavailable)
    result.assert_outcomes(passed=1, skipped=1)


@pytest.mark.parametrize("unavailable", ["missing-cli", "daemon", "image", "timeout"])
def test_required_unavailable_docker_fails_integration(pytester, monkeypatch, unavailable):
    result = run_integration_session(pytester, monkeypatch, True, unavailable)
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*EVOLOOP_REQUIRE_DOCKER=1*"])
