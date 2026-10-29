from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from .benchmark import Benchmark
from .evaluation import Evaluation, Evaluator
from .models import BudgetExhausted
from .strategy import Strategy, StrategyProposer


@dataclass
class RoundResult:
    number: int
    parent_id: str
    candidate: Strategy | None
    reason: str
    evaluation: Evaluation | None = None


@dataclass
class ExperimentReport:
    run_id: str
    created_at: str
    benchmark: dict[str, str]
    settings: dict[str, str | int]
    evidence: str
    baseline_strategy: Strategy
    selected_strategy: Strategy
    rounds: list[RoundResult] = field(default_factory=list)
    baseline_development: Evaluation | None = None
    holdout_baseline: Evaluation | None = None
    holdout_candidate: Evaluation | None = None
    complete: bool = False
    promotion_eligible: bool = False
    persisted: bool = False
    stop_reason: str = 'not_started'
    search_stop_reason: str = 'round_limit'
    calls_used: int = 0


class ImprovementLoop:
    def __init__(self, evaluator: Evaluator, proposer: StrategyProposer, rounds: int = 2,
                 model_name: str = 'mock', image: str = 'python:3.12-alpine', timeout: float = 5):
        if not 1 <= rounds <= 5:
            raise ValueError('rounds must be between 1 and 5')
        self.evaluator, self.proposer, self.round_limit = evaluator, proposer, rounds
        self.model_name, self.image, self.timeout = model_name, image, timeout

    def run(self, benchmark: Benchmark, baseline: Strategy) -> ExperimentReport:
        budget = self.evaluator.budget
        report = ExperimentReport(uuid.uuid4().hex, datetime.now(timezone.utc).isoformat(),
            {'id': benchmark.id, 'sha256': benchmark.fingerprint,
             'development_sha256': benchmark.split_hash('development'), 'holdout_sha256': benchmark.split_hash('holdout')},
            {'model': self.model_name, 'round_limit': self.round_limit, 'call_limit': budget.limit,
             'attempt_limit': self.evaluator.agent.max_attempts, 'image': self.image, 'timeout': str(self.timeout)},
            'synthetic workflow demonstration; not evidence of model learning' if self.model_name == 'mock'
            else 'single experimental sample; not evidence of statistically significant improvement', baseline, baseline)

        def finish(reason: str, complete: bool = False) -> ExperimentReport:
            report.stop_reason, report.complete, report.calls_used = reason, complete, budget.used
            return report

        def fault(evaluation: Evaluation) -> str:
            return 'budget_exhausted' if evaluation.failure_kind == 'budget' else f'{evaluation.failure_kind}_error'

        dev = benchmark.development
        initial = self.evaluator.evaluate(dev, baseline)
        report.baseline_development = initial
        if not initial.complete:
            return finish(fault(initial))
        best = initial
        stale = 0
        seen = {baseline.id}
        for number in range(1, self.round_limit + 1):
            parent = report.selected_strategy
            try:
                budget.consume()
                text = self.proposer.propose(parent, best.feedback(dev))
            except BudgetExhausted:
                report.rounds.append(RoundResult(number, parent.id, None, 'budget_exhausted'))
                return finish('budget_exhausted')
            except Exception:
                report.rounds.append(RoundResult(number, parent.id, None, 'model_error'))
                return finish('model_error')
            try:
                candidate = Strategy.create(text, parent.id)
            except ValueError:
                report.rounds.append(RoundResult(number, parent.id, None, 'invalid_strategy'))
                stale += 1
            else:
                entry = RoundResult(number, parent.id, candidate, 'duplicate')
                report.rounds.append(entry)
                if candidate.id in seen:
                    stale += 1
                else:
                    seen.add(candidate.id)
                    evaluation = self.evaluator.evaluate(dev, candidate)
                    entry.evaluation = evaluation
                    if not evaluation.complete:
                        entry.reason = 'incomplete'
                        return finish(fault(evaluation))
                    if evaluation.passed > best.passed:
                        best, report.selected_strategy = evaluation, candidate
                        entry.reason, stale = 'development_improved', 0
                    else:
                        entry.reason = 'no_development_improvement'
                        stale += 1
            if stale >= 2:
                report.search_stop_reason = 'two_rounds_without_improvement'
                break
        if report.selected_strategy.id == baseline.id:
            return finish('no_improvement', True)
        # Selection is frozen. No proposals or candidate changes after this point.
        report.holdout_baseline = self.evaluator.evaluate(benchmark.holdout, baseline)
        if not report.holdout_baseline.complete:
            return finish(fault(report.holdout_baseline))
        report.holdout_candidate = self.evaluator.evaluate(benchmark.holdout, report.selected_strategy)
        if not report.holdout_candidate.complete:
            return finish(fault(report.holdout_candidate))
        report.promotion_eligible = report.holdout_candidate.passed >= report.holdout_baseline.passed
        return finish('promotion_eligible' if report.promotion_eligible else 'holdout_regression', True)
