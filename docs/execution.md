# Agent execution: engineering prototype

The prototype now executes tasks rather than only listing planned episodes. It has a reactive worker loop, controlled tools, capability discovery, delegated conversion tasks, shared budgets, a durable SQLite journal, and independent final-state checks. This increment does not complete all milestones in the research specification.

## Run and inspect

```sh
uv sync --locked
uv run --locked agentflow run configs/fixture-smoke.json --output artifacts/fixture-001
uv run --locked agentflow run configs/fixture-smoke.json --output artifacts/fixture-001 --resume
```

The 72-episode campaign uses deterministic workers with no model provider. Agents operate on two synthetic tasks: update a record, and discover a unit mismatch that requires a converter. The latter suspends the parent, discovers another agent, passes a bounded child task, and resumes the parent with the returned conversion.

An output directory contains `run_plan.json`, `campaign.sqlite`, one episode database per executed episode, `episodes.jsonl`, `events.jsonl`, `usage.jsonl`, and `metrics.json`. Databases contain private execution state and are for the experiment operator, not for workers. Metrics are marked `research_results: false`. The 72 fixture successes are implementation checks and do not support claims about model competence or superiority of a routing method.

A fresh run refuses an existing directory. Resume checks the normalized configuration, execution source hash, and worker settings. Completed episodes are reused; unfinished episodes reconstruct their state from SQLite. The campaign ledger retains reservations across restarts. An operating-system lock permits one campaign runner at a time. This implementation targets macOS and Linux.

## Live model worker

`ChatWorker` connects to a Chat Completions endpoint. Model output must select exactly one tool, capability request, or submission. No model-generated Python or shell command is executed. The provider receives the worker's goal, permitted tool descriptions, input, and delivered observations. It does not receive the private grader, registry, or outage schedule.

Create a local provider settings file, substituting your endpoint and exact model ID:

```json
{
  "base_url": "https://api.openai.com/v1",
  "model": "YOUR_MODEL_ID",
  "api_key_env": "OPENAI_API_KEY",
  "max_completion_tokens": 512,
  "timeout_seconds": 60,
  "credits_per_call": 500
}
```

Configure the named environment variable through your usual secret-management process, then run:

```sh
uv run --locked agentflow run configs/agent-smoke.json --mode live --provider provider.local.json --output artifacts/live-001
```

The smaller smoke configuration contains six episodes, a 60-tick lease, and at most ten model requests per episode. Live mode rejects campaigns larger than twelve episodes. HTTPS is required except for explicit loopback endpoints; redirects are rejected. The provider must support the requested API fields and return usage. There is no fallback to a different model or automatic request retry.

The base campaign describes the fixture environment. The execution manifest separately records the effective live worker and hashes its provider settings and prompt into the execution identities. `plan` remains offline; `run` resolves the prototype execution profile. This is not a fully validated main-study manifest.

The adapter uses `max_completion_tokens` and JSON output mode, then validates the returned action locally. Completion usage already includes reasoning where the provider reports it that way; original usage is preserved without adding reasoning a second time. See the [official API contract](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create).

**Accounting limit:** `credits_per_call` is a fixed experimental charge, not a provider price or guaranteed currency cap. Token usage is recorded; billing cost remains unknown. The call count and requested completion limit bound the smoke workload. A real currency reservation model and provider-specific usage validation are still required before a budget-controlled research run. Fixture-only accounting uses UTF-8 byte counts as synthetic input/output units; these are not tokenizer measurements.

## Persistence and failure semantics

State, command responses, effects, reservations, and journal entries commit in one SQLite transaction. Duplicate command IDs return the recorded response; changed payloads conflict. A repeated approved tool operation can return its saved effect receipt, including after a restart. Tool calls still incur their request cost. The fixture tools prepare a copied state and change the canonical state only within the transaction.

An assignment has an epoch and input version. Old attempts cannot commit. A tool completion at lease expiry is rejected. A submitted result remains checkable if its worker subsequently goes offline. While waiting for a child, the parent lease pauses but the root deadline and budget continue. The prototype permits the one conversion dependency needed by these fixtures; arbitrary nested task graphs are not yet supported.

A model request is reserved and journaled before contacting a provider. If its outcome is uncertain, recovery marks it `UNKNOWN`, keeps the reservation, and terminates that episode without resending. Known usage is settled even for an invalid model action. Infrastructure programming errors propagate rather than becoming invented model results. Output limits and malformed replies are covered with a test transport; a successful public-provider run must be recorded separately.

Operational checks deliberately use public, weak criteria. A worker can claim completion and pass those checks while the private end-state grader reports failure. Goal correctness and forbidden changes therefore remain distinct from operational acceptance.

## Routing and research limits

The central policy accumulates paid observations. The intent policy matches local subscriptions and transfers discovery to a local broker. Referral routing visits local brokers in bounded waves and then uses the remaining central frontier as fallback. Each search shares contact and hop limits; repeated attempts do not get a fresh contact allowance. All three use the same worker and effect runtime.

These are fixture-level implementations, not replicas of RAPS or AgentNet. Capability IDs and subscriptions are intentionally simple, and historical evidence is an empty fixture snapshot represented by the configured priors. This does not test the research hypothesis about informative referral history.

Execution is serialized, within the configured concurrency ceiling. Referral waves are processed sequentially. Task state is currently stored as a transactional JSON projection with a command journal, rather than the final normalized task/outbox schema. Transport duplication is covered by command deduplication; a separately scheduled network outbox, general asynchronous routing, observed-availability TTL caching, opaque contact pagination, diagnostic policies, full transcript replay, and independent-process benchmark isolation remain future work. The private grader runs only after episode termination and has no worker-callable interface.

WorkBench execution, full message schemas, provenance-complete study manifests, statistical analysis, and live billing constraints remain open. Do not treat passing fixtures as full acceptance of M0–M6.
