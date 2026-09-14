# WorkBench compatibility and provenance audit

Audit date: 2026-09-13. This is a source inspection, not an executed adapter acceptance test.

## Inspected source

The [paper](https://arxiv.org/html/2405.00823v2) points to `olly-styles/WorkBench`. The inspected repository revision is [`49c7dfd00c03d384ec59ea57374f50b766aa5613`](https://github.com/olly-styles/WorkBench/tree/49c7dfd00c03d384ec59ea57374f50b766aa5613). This is an integration candidate, not yet the frozen study benchmark.

The repository [LICENSE](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/LICENSE) is MIT, copyright 2024 Mindsdb. No upstream code or dataset is bundled with Tweetflows at this stage. Preserve the upstream notice when integrating licensed material and record the exact data files used.

## Python and environment compatibility

The inspected [pyproject.toml](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/pyproject.toml) declares Python 3.12 or later, compatible with Tweetflows' 3.12 target. It requires uv 0.10.12 or later for its own project environment. Tweetflows' planning package does not import or install WorkBench. Installing and running the complete upstream dependency set is still pending.

## State and effect boundary

[ToolState](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/src/tools/state.py) stores sandbox tables in pandas objects and provides copy/reset operations. State access is thread-local; this must not be assumed to provide isolation between asynchronous tasks on the same thread. The [email tools](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/src/tools/email.py) mutate that state. They do not implement Tweetflows' transactional prepare/commit contract.

The adapter must execute operations against an isolated state copy, capture all resulting state, and commit it through the runtime after checking authorization and revision. No direct mutation of the canonical state is permitted. Before adoption, verify serialization fidelity, deterministic replay, plotting/file effects, and isolation for every enabled tool. Upstream [state-isolation tests](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/tests/tools/test_state_isolation.py) are useful context; they are not evidence that Tweetflows acceptance test T22 passes.

## Dataset and grader version

The current [upstream README](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/README.md) distinguishes original data from corrected 2026 ground truth and describes changes to scoring. An unpinned checkout must not silently replace the paper's data or evaluator.

Before a live pilot, record the task-file hashes, template split, ground-truth version, evaluator hash, and all task modifications. The private evaluator must remain inaccessible during agent execution. Published 2024 scores and scores from a later evaluator are not automatically comparable.

## Decision

Retain WorkBench as the first adapter candidate. Python requirements and the inspected repository license support further implementation. Runtime compatibility, dataset selection, and T22 remain open. M0 is therefore partially complete; this audit does not certify a runnable WorkBench experiment.
