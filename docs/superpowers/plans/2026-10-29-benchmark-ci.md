# Expanded benchmark and CI plan

User requested expansion of the benchmark and CI after the mock RSI milestone. Proceed inline on codex/benchmark-ci, based on local main b1c4a0a; do not change the existing demo or merge the prior PR automatically.

**Scope:** 24 original Python tasks, frozen 16/8 development/holdout split, explicit public function signatures, >=6 deterministic cases per task; trusted reference functions live only in tests. Package JSON data with the distribution. Add CLI selection and offline catalog. Preserve mock demo semantics; disallow scoring the core suite with the canned mock client.

**Architecture:** data/core_v1.json → load_benchmark(name) → existing Benchmark snapshots/Agent/evaluator. CLI uses --benchmark demo|core. Integration tests compile reference source exclusively inside Docker and evaluate every task. CI runs all tests on Ubuntu with Python 3.12/3.13/3.14, requires Docker, and uploads JUnit reports even on failure.

**Interfaces:** load_benchmark(name: str) -> Benchmark, benchmark_catalog() -> list[dict[str, str | int]]. Existing demo_benchmark() and Benchmark are preserved. EVOLOOP_REQUIRE_DOCKER=1 makes integration preflight failures fatal; local absence continues to skip.

## Tasks

- [ ] Tests first for core split size/IDs/metadata/snapshot/hash, malformed input, references/expected cases, CLI catalog/selection/mock restriction and resource packaging.
- [ ] Add dataset, loader, packaging and CLI with documented budgets (two-round worst case 194 calls; do not silently raise the default limit).
- [ ] Independently implement CI and strict Docker gating, testing available/unavailable/required paths.
- [ ] Validate every reference solution through actual Docker, run the full local suite, inspect built wheel data.
- [ ] Review and fix issues. Push reviewable changes and run GitHub CI; do not claim hosted success until runs actually finish.

## Review focus

- Do not copy known benchmark solutions into runtime clients or proposer feedback.
- No overlap in task IDs and no automatic random re-splitting.
- CI must fail if Docker cannot execute tests, rather than pass with skips.
- Handle CI Python 3.12 resource loading/packaging and Linux test imports.
- Preserve the existing demonstration and upper model-call budgets.

## Ledger

Baseline: 50 passed, 6 skipped (Docker unavailable in current environment). Original code had 56 passing tests when Docker was running. CI implementation delegated with disjoint file ownership.

Implemented: 24 tasks with 156 cases; 16 development and 8 holdout tasks. JSON schema, fixed hash, resource packaging, CLI catalog and explicit suite selection covered. Demo behavior retained. Reference implementations exist only in tests.

RED→GREEN: missing loader/catalog; missing reference source; CLI selection/catalog; boolean schema version accepted as integer; required-Docker policy initially 8 failures then 10 passing policy tests.

Local verification: 100 passed, 30 skipped in 3.09s. Docker Desktop could not start its engine; the missing pipe was rechecked. The 30 integration cases are intentionally not claimed as locally passing. Strict CI requires Docker and will fail on missing daemon/image.

Packaging verification: isolated `python -I` imports directly from built wheel and matches source hash e44f2a2ae219226c8126cdb398dad832462e33d6455efafa746e7f08d10de30d; wheel contains JSON and excludes reference tests. Local no-build-isolation attempt initially failed because the venv lacked setuptools; normal isolated build succeeded.

Review: independent reviewer checked all task descriptions and independently validated all 156 expected outputs with no mismatches, and found no Important/Critical issues in loader/splits/prompt separation/Docker gate. Reviewer's remaining CI/package pass was interrupted by tool usage limits; parent completed those checks, including official Action ref verification and isolated wheel import. Hosted matrix verification is pending.

Ruling: --benchmark core is opt-in and incompatible with canned mock scoring. This preserves the synthetic demo and prevents presenting predetermined mock accuracy as core performance. Native Docker failure will be reported; hosted CI is the authoritative complete integration check for this change.
