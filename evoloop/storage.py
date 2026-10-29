from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from .improvement import ExperimentReport
from .strategy import Strategy, BASELINE_TEXT


def atomic_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_strategy(path: Path) -> Strategy:
    data = json.loads(path.read_text(encoding='utf-8'))
    strategy = Strategy.create(data['text'], data.get('parent_id'))
    if data['id'] != strategy.id:
        raise ValueError('Strategy content hash mismatch')
    return strategy


class StrategyStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def load(self) -> Strategy:
        path = self.directory / 'active_strategy.json'
        if not path.exists():
            return Strategy.create(BASELINE_TEXT)
        return read_strategy(path)

    def save(self, report: ExperimentReport) -> Path:
        report_path = self.directory / 'reports' / f'{report.run_id}.json'
        strategies = [report.baseline_strategy, *[r.candidate for r in report.rounds if r.candidate]]
        seen: set[str] = set()
        for strategy in strategies:
            if strategy.id in seen:
                continue
            seen.add(strategy.id)
            path = self.directory / 'strategies' / f'{strategy.id}.json'
            if not path.exists():
                atomic_json(path, asdict(strategy))
        # persisted means the audit report exists. Eligibility is distinct from active promotion.
        report.persisted = True
        try:
            atomic_json(report_path, asdict(report))
            if report.promotion_eligible:
                atomic_json(self.directory / 'active_strategy.json', asdict(report.selected_strategy))
        except OSError:
            report.persisted = False
            raise
        return report_path
