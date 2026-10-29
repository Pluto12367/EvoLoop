# Python Core v1

An original, small functional benchmark for EvoLoop. Source: `evoloop/data/core_v1.json` (schema version 1). It contains 24 tasks and 156 cases, frozen into 16 development tasks and 8 holdout tasks; no random split occurs at runtime. The CLI reports the benchmark and split hashes.

The model receives only each public description, function name and ID. The strategy proposer receives development feedback only. Full test cases stay with the evaluator, but the repository and reference tests are public; this is not a secret or contamination-resistant benchmark. The 4-task synthetic demo is a different suite with a separate hash and purpose.

| Split | Function | Category | Difficulty |
| --- | --- | --- | --- |
| Development | prefix_sums | sequences | easy |
| Development | run_length_encode | strings | easy |
| Development | word_counts | mappings | easy |
| Development | stable_partition | sequences | easy |
| Development | binary_search_first | search | medium |
| Development | merge_intervals | intervals | medium |
| Development | longest_unique_substring | strings | medium |
| Development | gcd_list | numeric | easy |
| Development | parse_int_list | parsing | medium |
| Development | two_sum_indices | search | medium |
| Development | balanced_brackets | parsing | easy |
| Development | min_coin_count | dynamic programming | medium |
| Development | transpose | matrices | easy |
| Development | flatten_once | sequences | easy |
| Development | top_k_frequent | mappings | medium |
| Development | max_subarray_sum | dynamic programming | medium |
| Holdout | product_except_self | numeric | medium |
| Holdout | rotate_right | sequences | easy |
| Holdout | group_anagrams | mappings | medium |
| Holdout | lower_bound | search | medium |
| Holdout | interval_intersections | intervals | medium |
| Holdout | levenshtein_distance | dynamic programming | hard |
| Holdout | count_paths | matrices | medium |
| Holdout | evaluate_rpn | parsing | hard |

Difficulty labels are relative editorial labels, not measured model difficulty. Development and holdout IDs are disjoint, but algorithmic families can overlap to allow transfer; the split is not a claim of independence from a model's training data.

Each task has at least six cases. Cases cover empty and singleton inputs, negative numbers, duplicates and tie-breaking, Unicode, malformed tokens, zeros, ordering, endpoint-only interval intersections, non-greedy coin choices, obstacles, and large exact integer arithmetic where applicable. Inputs outside the public preconditions are not scored.

`tests/reference_solutions.py` contains ordinary trusted Python reference functions, not lookup tables. Fast tests call these trusted functions directly and compare every expected answer; integration tests send each function's source to the Docker executor. Model-generated code is never executed in the host process. Runtime packaging excludes all tests and reference implementations.

The suite tests outputs, not algorithmic complexity. Its small sample size and publicly visible cases cannot establish general intelligence, model training, statistically significant gains, or judge-tampering resistance. Repeatedly tuning against the same holdout invalidates its role as a final check; create a new version for material task/test changes and use a fresh final suite for serious claims.

For two improvement rounds, a conservative budget is `3*16 + 2*(1 + 3*16) + 2*3*8 = 194` calls. This counts both proposals and worst-case solution retries for both final holdout evaluations. An exhausted budget still stops the experiment without adoption, regardless of the selected suite. No real model API calls are made by the reference tests or CI.
