# RSI Strategy Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task with tests first.

**Goal:** Validate bounded strategy improvement with a synthetic model and independent holdout.
**Architecture:** Public task views, budgeted Agent evaluations, development selection, one final holdout comparison, atomic JSON strategy storage.
**Tech Stack:** Python 3.12+, dotenv, pytest, Docker, standard library.
**Spec:** ../specs/2026-10-29-rsi-strategy-design.md

## Global Constraints

Every task: no test leakage to clients/proposer; no host execution; at most 3 attempts per task, 1–5 improvement rounds, default 100 model calls. No real model calls without configuration. Synthetic results are workflow evidence only.

## Review Focus

- Infrastructure faults and exhausted budgets must abort adoption, preserving partial attempts.
- Mutable test inputs must not affect subsequent evaluations.
- Holdout must not enter proposal context; candidate freezes before holdout.
- Failed writes must preserve previous active strategy.
- Reloaded active strategy must become the next experiment baseline.

## Tasks

### 1. Private evaluation inputs and failures
Modify models/interfaces/agent/clients/executor; tests/test_agent.py and test_executor.py.
Produce TaskSpec, explicit failure_kind on results/attempts, optional strategy argument.
- [x] Write and run failing privacy, fault classification and input-copy tests.
- [x] Implement public task views, optional strategy prompts and per-test deep copies.
- [x] Run full pytest; preserve existing client compatibility when strategy is absent.

### 2. Strategies, benchmark, budgeted evaluation
Create strategy.py, benchmark.py, evaluation.py and corresponding tests.
Produce Strategy.create(text,parent_id), Benchmark snapshot/hash validation, CallBudget.consume(), Evaluator.evaluate(problems,strategy).
- [x] Tests first: version validation, disjoint nonempty suites, snapshots, hard call budget, partial records.
- [x] Implement fixed synthetic benchmark and strategy-sensitive mock/proposer.
- [x] Run full pytest.

### 3. Improvement loop and persistence
Create improvement.py, storage.py and corresponding tests.
Produce ImprovementLoop.run(benchmark,baseline), StrategyStore.load()/save(report).
- [x] Tests first: promotion, tie rejection, holdout regression, duplicate/invalid strategy, faults, budget, atomic writes.
- [x] Implement bounded rounds, freeze final candidate, single final holdout gate and report-before-active writes.
- [x] Run full pytest.

### 4. CLI and validation
Modify cli.py, README.md, .gitignore and integration tests.
- [x] Tests first for --improve JSON, state reload, CLI error exit, full mock Docker experiment.
- [x] Implement --rounds/--max-model-calls/--state-dir/--strategy-file and accurate synthetic labeling.
- [x] Run full pytest, real Docker tests when available, CLI smoke runs; independently review final change.

## Execution ledger

Ruling: work in a new feature branch in the existing checkout; no additional worktree created because it needs separate consent. This keeps the user's active project directory usable; main stays unchanged.
Ruling: user explicitly requested simulation-first implementation after the design discussion; proceed inline without another planning approval.
Pre-flight: TaskSpec and Strategy feed Agent/Evaluator; evaluation results feed Loop; report types feed Store/CLI. No conflicting interfaces found.

Task 1: complete — public task privacy and structured failure tests RED→GREEN; full suite 15 passed, 4 Docker skips before engine startup.
Task 2: complete — strategy, benchmark snapshot and budget tests initially failed on missing modules, then passed; full suite 19 passed, 4 skips.
Task 3: complete — loop/storage tests initially failed on missing modules, then passed; full suite 30 passed, 4 skips. Native test execution required because sandbox pytest temp directories reject restrictive directory permissions.
Task 4: implementation complete — CLI test RED→GREEN; Docker Desktop started successfully; full suite 42 passed including complete mock/Docker improvement experiment. Additional boundary tests: 26 core/improvement tests passed.
Verification: CLI first run runs/verified-demo — dev 0→1, holdout candidate 1, 18 model calls, eligible/persisted; reload run — selected strategy restored, no_improvement, 4 calls.
Final: fixed duplicate archive overwriting original parent — test_archive_preserves_original_parent_for_duplicate_strategy RED→GREEN, then suite 42 passed.
Ruling: report promotion_eligible is the evaluation decision; persisted means audit save succeeded, active_strategy.json is authoritative for activation. This avoids claiming a multi-file transaction; if disk fails, CLI reports storage_error and previous active remains.

Final review: independent reviewer found two Important issues, both fixed with failing regression tests first: solution process exits now retry as solution failures; every failure category now uses sanitized summaries. Proposal-error audit records were also fixed RED→GREEN. Mutable-input and late-fault coverage passed. No deferred findings remain.
Final verification: 56 passed in 43.28s, zero skips, including real Docker full improvement and abnormal-exit retry. CLI budget=1 stopped at one call and retained active file hash. Original sample/report.json retained locally and ignored. No real model calls made.
