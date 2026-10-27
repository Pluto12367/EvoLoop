import argparse
from dataclasses import asdict
import json
import os
import sys
from dotenv import load_dotenv
from .agent import Agent
from .clients import MockModelClient, OpenAICompatibleClient
from .examples import example_problems
from .executor import DockerExecutor
from .models import Status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run EvoLoop example problems')
    parser.add_argument('--model', choices=['mock', 'openai-compatible'], default='mock')
    parser.add_argument('--image', default='python:3.12-alpine')
    parser.add_argument('--timeout', type=float, default=5)
    args = parser.parse_args(argv)
    load_dotenv()
    if args.model == 'mock':
        client = MockModelClient()
    else:
        key, url, model = (os.getenv(k) for k in ('EVOLOOP_API_KEY', 'EVOLOOP_BASE_URL', 'EVOLOOP_MODEL'))
        if not all((key, url, model)):
            print('Set EVOLOOP_API_KEY, EVOLOOP_BASE_URL and EVOLOOP_MODEL', file=sys.stderr)
            return 2
        client = OpenAICompatibleClient(url, key, model)
    agent = Agent(client, DockerExecutor(args.image, args.timeout))
    results = [agent.solve(problem) for problem in example_problems()]
    print(json.dumps({'problems': [asdict(result) for result in results]}, ensure_ascii=False, indent=2))
    return 0 if all(result.attempts[-1].test_result == Status.PASSED for result in results) else 1
