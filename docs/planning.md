# Fixture planning contract

Version 1.0 supports validation and design expansion only. It implements the planning requirement T21 from the [technical specification](specification.md). Runtime acceptance requirements are not covered by successful planning.

## Input

The packaged [JSON Schema](../src/tweetflows/schemas/campaign.schema.json) uses Draft 2020-12 and is resolved locally. All declared fields are required and additional fields are rejected, including inside nested objects. Unknown adapters and fixture references are rejected rather than treated as installed implementations. Only the three main methods, development fixtures, deterministic mock model, fixed durations, and frozen history are supported in this initial contract.

Cross-field checks enforce cardinality declarations, visibility counts, root versus search contact limits, score sums, child depth, primary-method membership, and an episode reservation that fits the campaign limit. Invalid input exits with status 2 and an explanatory message. Duplicate JSON keys and non-finite numbers are rejected.

The configuration is copied and normalized, leaving caller input unchanged. Method, task, regime, and replicate-seed collections are treated as sets and sorted. The order of `analysis.primary_pair` is retained because it defines the contrast direction.

## Output and identity

The plan includes the normalized configuration, schema hash, planner source hash, configuration hash, and a plan hash over all other output fields. Hashing uses UTF-8 JSON with sorted keys, compact separators, and no non-finite numbers; it is this Python implementation's encoding contract, not a claim of RFC 8785 compliance.

Each `pair_id` includes the task, variant, regime, replicate seed, and shared infrastructure configuration. It excludes the method, campaign label, selected task/method lists, analysis settings, and aggregate campaign limit. Changing a per-episode budget changes the pair; reducing the method set preserves remaining episode identities. `episode_id` adds the method to the pair. IDs are scoped to their campaign storage; identical scientific designs may intentionally have identical IDs in different campaigns.

Independent named seed streams are derived for scenarios, topology, availability, operation durations, tie-breaking, and model sampling. All methods in a comparison group receive the same initial stream seeds. Stable regimes have no availability trace, even when a churn trace is configured for other regimes. Scenario contents and runtime event ordering still require implementation.

Hashes of reference names do not establish the contents of snapshots or historical evidence. The output therefore records `execution_ready: false` and lists missing execution artifacts. It is a planning artifact, not the final `manifest.resolved.json` specified for a runnable study. Installed package versions are locked in `uv.lock`; a future runtime manifest must additionally record the actual environment, execution code, and resource-content hashes.

## Budgets

`all_episodes_upper_bound` is the episode count multiplied by the per-episode cap. `all_episodes_guaranteed_fundable` indicates whether the campaign cap covers that worst case. A lower campaign cap is allowed if it can reserve at least one episode; it does not promise every planned episode will run. A future scheduler must reserve and settle that shared cap without dropping unexecuted episodes from reporting. Synthetic credits are not provider prices.

## Verification and remaining scope

Tests cover the 72-episode design, complete method groups, deterministic normalization, paired seeds, budget-sensitive IDs, inactive stable-regime faults, invalid input, offline CLI operation, and protection of existing output files.

M0 still requires execution message contracts and complete runtime artifact resolution. The [WorkBench source audit](workbench-provenance.md) records the candidate source, license, and state-model implications; actual adapter compatibility and T22 are pending. The next runtime increment is the transactional task/attempt journal and budget reservation model from M1.
