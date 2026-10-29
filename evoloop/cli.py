import argparse
from dataclasses import asdict
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from .agent import Agent
from .clients import MockModelClient, OpenAICompatibleClient
from .examples import example_problems
from .executor import DockerExecutor
from .models import Status
from .strategy import MockStrategyClient, MockStrategyProposer, ModelStrategyProposer
from .benchmark import demo_benchmark
from .evaluation import CallBudget, Evaluator
from .improvement import ImprovementLoop
from .storage import StrategyStore, read_strategy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run EvoLoop example problems')
    parser.add_argument('--model', choices=['mock', 'openai-compatible'], default='mock')
    parser.add_argument('--image', default='python:3.12-alpine')
    parser.add_argument('--timeout', type=float, default=5)
    parser.add_argument('--improve', action='store_true')
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--max-model-calls', type=int, default=100)
    parser.add_argument('--state-dir', type=Path, default=Path('runs/default'))
    parser.add_argument('--strategy-file', type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.rounds <= 5 or args.max_model_calls < 1 or args.timeout <= 0:
        parser.error('rounds must be 1–5, model call budget and timeout must be positive')
    if args.improve and args.strategy_file:
        parser.error('--strategy-file is for ordinary solving; improvement loads its state directory')
    load_dotenv()
    if args.model == 'mock':
        client = MockModelClient()
    else:
        key, url, model = (os.getenv(k) for k in ('EVOLOOP_API_KEY', 'EVOLOOP_BASE_URL', 'EVOLOOP_MODEL'))
        if not all((key, url, model)):
            print('Set EVOLOOP_API_KEY, EVOLOOP_BASE_URL and EVOLOOP_MODEL', file=sys.stderr)
            return 2
        client = OpenAICompatibleClient(url, key, model)
    executor = DockerExecutor(args.image, args.timeout)
    if args.improve:
        if args.model == 'mock':
            client, proposer = MockStrategyClient(), MockStrategyProposer()
        else:
            proposer = ModelStrategyProposer(client)
        store = StrategyStore(args.state_dir)
        try:
            baseline = store.load()
        except (OSError, ValueError, KeyError, TypeError):
            print(json.dumps({'complete': False, 'stop_reason': 'invalid_strategy_state'}))
            return 2
        evaluator = Evaluator(client, executor, CallBudget(args.max_model_calls))
        name = 'mock' if args.model == 'mock' else f'{args.model}:{model}'
        report = ImprovementLoop(evaluator, proposer, args.rounds, name, args.image, args.timeout).run(demo_benchmark(), baseline)
        try:
            store.save(report)
        except (OSError, ValueError):
            report.stop_reason, report.complete, report.persisted = 'storage_error', False, False
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        return 0 if report.complete and report.persisted else 1
    agent = Agent(client, executor)
    try:
        strategy = read_strategy(args.strategy_file).text if args.strategy_file else None
    except (OSError, ValueError, KeyError, TypeError):
        print('Invalid strategy file', file=sys.stderr)
        return 2
    results = [agent.solve(problem, strategy) for problem in example_problems()]
    print(json.dumps({'problems': [asdict(result) for result in results]}, ensure_ascii=False, indent=2))
    return 0 if all(result.attempts[-1].test_result == Status.PASSED for result in results) else 1
