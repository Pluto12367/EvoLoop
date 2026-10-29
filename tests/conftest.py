"""Shared integration-test policy; image preparation is an explicit CI step."""

import os
import subprocess

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: requires Docker and the python:3.12-alpine image"
    )


@pytest.fixture(scope="session")
def docker_unavailable_reason():
    probes = [
        (["docker", "info"], "Docker daemon unavailable"),
        (
            ["docker", "image", "inspect", "python:3.12-alpine"],
            "python:3.12-alpine image unavailable; run docker pull python:3.12-alpine",
        ),
    ]
    for command, reason in probes:
        try:
            result = subprocess.run(command, capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"{reason}: {exc}"
        if result.returncode != 0:
            return reason
    return None


@pytest.fixture(autouse=True)
def require_docker_for_integration(request):
    if request.node.get_closest_marker("integration") is None:
        return
    reason = request.getfixturevalue("docker_unavailable_reason")
    if reason is None:
        return
    if os.environ.get("EVOLOOP_REQUIRE_DOCKER") == "1":
        pytest.fail(f"Docker required by EVOLOOP_REQUIRE_DOCKER=1: {reason}", pytrace=False)
    pytest.skip(reason)
