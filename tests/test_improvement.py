from dataclasses import asdict
import json
import pytest
from evoloop.strategy import Strategy, BASELINE_TEXT, MockStrategyClient, MockStrategyProposer
from evoloop.benchmark import demo_benchmark
from evoloop.evaluation import CallBudget, Evaluator
from evoloop.improvement import ImprovementLoop
from evoloop.storage import StrategyStore
from evoloop.models import ExecutionResult, Status


class FixtureExecutor:
    def __init__(self, regress=False): self.regress = regress
    def run(self, problem, code):
        failed = 'return None' in code or (self.regress and problem.id == 'evens')
        return ExecutionResult(Status.FAILED if failed else Status.PASSED, 0, 'case 1 failed' if failed else None)


def experiment(limit=100, regress=False, proposer=None):
    budget = CallBudget(limit)
    return ImprovementLoop(Evaluator(MockStrategyClient(), FixtureExecutor(regress), budget),
                           proposer or MockStrategyProposer(), rounds=2).run(demo_benchmark(), Strategy.create(BASELINE_TEXT))


def test_improvement_promotes_and_records_every_evaluation():
    report = experiment()
    assert report.complete and report.promotion_eligible
    assert report.baseline_development.pass_rate == 0
    assert report.rounds[0].evaluation.pass_rate == 1
    assert report.holdout_candidate.pass_rate == 1
    assert report.selected_strategy.parent_id == report.baseline_strategy.id
    assert report.calls_used <= 100
    assert report.rounds[1].reason == 'duplicate'
    assert 'synthetic' in report.evidence


def test_holdout_regression_rejects():
    # Baseline passes holdout; a candidate regresses on exactly one holdout task.
    class Client(MockStrategyClient):
        def generate(self, task, feedback, *, strategy=''):
            if task.id in ('squares', 'evens'):
                if strategy == BASELINE_TEXT: return 'def f(): return 1'
                if task.id == 'evens': return 'def f(): return None'
            return super().generate(task, feedback, strategy=strategy)
    report = ImprovementLoop(Evaluator(Client(), FixtureExecutor(), CallBudget()), MockStrategyProposer()).run(demo_benchmark(), Strategy.create(BASELINE_TEXT))
    assert report.complete and not report.promotion_eligible
    assert report.stop_reason == 'holdout_regression'


@pytest.mark.parametrize('limit', [1, 6, 7, 9, 10])
def test_incomplete_budget_never_promotes(limit):
    report = experiment(limit)
    assert not report.promotion_eligible
    assert report.calls_used <= limit
    assert report.stop_reason == 'budget_exhausted'
    assert report.baseline_development.results


def test_proposer_never_receives_holdout_or_tests():
    class Proposer:
        def propose(self, current, feedback):
            data = json.dumps([asdict(f) for f in feedback])
            assert 'squares' not in data and 'evens' not in data
            assert 'tests' not in data and 'code' not in data and 'expected' not in data
            return current.text
    report = experiment(proposer=Proposer())
    assert report.stop_reason == 'no_improvement'
    assert report.holdout_candidate is None


def test_model_failure_aborts():
    class Client:
        def generate(self, *args, **kwargs): raise ValueError('secret')
    report = ImprovementLoop(Evaluator(Client(), FixtureExecutor(), CallBudget()), MockStrategyProposer()).run(demo_benchmark(), Strategy.create(BASELINE_TEXT))
    assert not report.complete and not report.promotion_eligible
    assert report.stop_reason == 'model_error'
    assert 'secret' not in json.dumps(asdict(report))


def test_store_roundtrip_and_failed_write_preserves_active(tmp_path, monkeypatch):
    store = StrategyStore(tmp_path)
    report = experiment()
    store.save(report)
    assert store.load() == report.selected_strategy
    original = (tmp_path / 'active_strategy.json').read_bytes()
    import evoloop.storage as storage
    def fail(*args): raise OSError('write failed')
    monkeypatch.setattr(storage.os, 'replace', fail)
    with pytest.raises(OSError): store.save(experiment())
    assert (tmp_path / 'active_strategy.json').read_bytes() == original


def test_rejected_experiment_preserves_active(tmp_path):
    store = StrategyStore(tmp_path)
    adopted = experiment()
    store.save(adopted)
    rejected = experiment(limit=1)
    store.save(rejected)
    assert store.load() == adopted.selected_strategy


def test_archive_preserves_original_parent_for_duplicate_strategy(tmp_path):
    report = experiment()
    StrategyStore(tmp_path).save(report)
    archived = json.loads((tmp_path / 'strategies' / f'{report.selected_strategy.id}.json').read_text())
    assert archived['parent_id'] == report.baseline_strategy.id


def test_final_active_write_failure_preserves_old_strategy(tmp_path, monkeypatch):
    store = StrategyStore(tmp_path)
    initial = experiment()
    store.save(initial)
    original = (tmp_path / 'active_strategy.json').read_bytes()
    import evoloop.storage as storage
    replace = storage.os.replace
    def fail_active(source, target):
        if target.name == 'active_strategy.json': raise OSError('failed')
        return replace(source, target)
    monkeypatch.setattr(storage.os, 'replace', fail_active)
    with pytest.raises(OSError): store.save(experiment())
    assert (tmp_path / 'active_strategy.json').read_bytes() == original


@pytest.mark.parametrize('text', [' ', 'x' * 4001])
def test_invalid_candidates_stop_after_two_rounds(text):
    class Proposer:
        def propose(self, *args): return text
    report = experiment(proposer=Proposer())
    assert len(report.rounds) == 2
    assert all(r.reason == 'invalid_strategy' for r in report.rounds)
    assert report.stop_reason == 'no_improvement'


def test_candidate_tie_is_rejected():
    class Proposer:
        def propose(self, *args): return 'Different but ineffective guidance'
    report = experiment(proposer=Proposer())
    assert report.rounds[0].reason == 'no_development_improvement'
    assert not report.promotion_eligible
    assert report.holdout_candidate is None


def test_infrastructure_failure_aborts_experiment():
    class Unavailable:
        def run(self, *args): return ExecutionResult(Status.UNAVAILABLE, 0, 'unavailable')
    report = ImprovementLoop(Evaluator(MockStrategyClient(), Unavailable(), CallBudget()), MockStrategyProposer()).run(demo_benchmark(), Strategy.create(BASELINE_TEXT))
    assert report.stop_reason == 'infrastructure_error'
    assert not report.promotion_eligible


@pytest.mark.parametrize('rounds', [0, 6])
def test_round_limit_is_validated(rounds):
    with pytest.raises(ValueError):
        ImprovementLoop(Evaluator(MockStrategyClient(), FixtureExecutor(), CallBudget()), MockStrategyProposer(), rounds)


def test_proposal_failure_aborts_without_exposing_error():
    class Proposer:
        def propose(self, *args): raise RuntimeError('secret')
    report = experiment(proposer=Proposer())
    assert report.stop_reason == 'model_error'
    assert report.calls_used == 7
    assert not report.promotion_eligible
    assert 'secret' not in json.dumps(asdict(report))


def test_proposal_error_round_is_recorded():
    class Proposer:
        def propose(self, *args): raise RuntimeError('secret')
    report = experiment(proposer=Proposer())
    assert len(report.rounds) == 1
    assert report.rounds[0].reason == 'model_error'


def test_late_model_failure_preserves_earlier_attempts():
    class Client(MockStrategyClient):
        calls = 0
        def generate(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 4: raise RuntimeError('secret')
            return super().generate(*args, **kwargs)
    report = ImprovementLoop(Evaluator(Client(), FixtureExecutor(), CallBudget()), MockStrategyProposer()).run(demo_benchmark(), Strategy.create(BASELINE_TEXT))
    assert report.stop_reason == 'model_error'
    assert len(report.baseline_development.results) == 2
    assert len(report.baseline_development.results[0].attempts) == 3
    assert report.baseline_development.results[1].attempts[0].failure_kind == 'model'
