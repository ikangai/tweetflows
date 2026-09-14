import copy
import io
import json
from pathlib import Path

import pytest

from tweetflows.config import canonical_json, load_campaign
from tweetflows.execution import run_campaign, run_episode
from tweetflows.fixtures import scenario
from tweetflows.live import ChatWorker
from tweetflows.planning import plan_campaign
from tweetflows.runtime import Runtime
from tweetflows.store import ExecutionError, Store

EXAMPLE = Path(__file__).parents[1] / "configs" / "fixture-smoke.json"


@pytest.fixture
def runtime(tmp_path):
    config = load_campaign(EXAMPLE)
    episode = next(
        e
        for e in plan_campaign(config)["episodes"]
        if e["task_instance_id"] == "direct_update" and e["regime_id"] == "full_stable"
    )
    current = Runtime(tmp_path / "episode.sqlite", config, episode, scenario(episode))
    yield current
    current.close()


def award(runtime):
    state = runtime.read()
    target = next(
        p["agent_id"]
        for p in state["views"]["initiator"]["profiles"].values()
        if "records" in p["capabilities"]
    )
    offered = runtime.command(
        "DISCOVER",
        {
            "actor": "initiator",
            "target": target,
            "op": "offer_request",
            "search": "root:records",
            "task_id": "root",
            "depth": 0,
        },
    )
    result = runtime.command("AWARD", {"task_id": "root", "offer_id": offered["offer_id"]})
    assert result["ok"]
    return offered


def queue(runtime, action):
    identity = runtime.identity("root")
    start = runtime.command("MODEL_START", {**identity, "upper_bound": 1, "request_hash": "test"})
    return runtime.command(
        "MODEL_FINISH", {**identity, "call_id": start["call_id"], "action": action, "cost": 1}
    )


def update_action(value=20):
    return {
        "kind": "tool",
        "tool": "update_record",
        "arguments": {"record_id": "order-1", "value": value, "unit": "mm"},
    }


def test_only_one_award_and_stale_input_fenced(runtime):
    offered = award(runtime)
    assert "error" in runtime.command("AWARD", {"task_id": "root", "offer_id": offered["offer_id"]})
    assert len(runtime.read()["attempts"]) == 1
    old = runtime.identity("root")
    runtime.command("INVALIDATE_INPUT", {"task_id": "root"})
    with pytest.raises(ExecutionError, match="STALE_ATTEMPT"):
        runtime.command("ACTION", old)


def test_duplicate_command_and_effect_receipt(runtime):
    award(runtime)
    queue(runtime, update_action())
    identity = runtime.identity("root")
    first = runtime.command("ACTION", identity, "same-command")
    before = runtime.read()
    assert runtime.command("ACTION", identity, "same-command") == first
    assert runtime.read() == before
    with pytest.raises(ExecutionError, match="IDEMPOTENCY_CONFLICT"):
        runtime.command("ACTION", {**identity, "epoch": 99}, "same-command")
    queue(runtime, update_action())
    runtime.command("ACTION", identity)
    assert runtime.read()["world"]["revision"] == 1
    assert len(runtime.read()["effects"]) == 1


def test_transaction_rollback_and_reopen(tmp_path):
    path = tmp_path / "state.sqlite"
    store = Store(path, {"value": 0})

    def crash(state, events):
        state["value"] = 99
        events.append({"kind": "BAD"})
        raise RuntimeError("injected crash before commit")

    with pytest.raises(RuntimeError):
        store.apply("bad", {}, crash)
    store.close()
    reopened = Store(path)
    assert reopened.read() == {"value": 0}
    assert reopened.events() == []
    reopened.close()


def test_interrupted_model_call_keeps_reservation_and_never_resends(runtime):
    award(runtime)
    runtime.command(
        "MODEL_START", {**runtime.identity("root"), "upper_bound": 100, "request_hash": "unknown"}
    )

    class NeverCall:
        def decide(self, view):
            pytest.fail("Uncertain request was resent")

    result = run_episode(runtime, NeverCall())
    assert result["reason"] == "UNKNOWN_MODEL_CALL"
    assert result["reserved"] == 100
    assert not result["success"]


def test_model_reservation_cannot_exceed_root_cap(runtime):
    award(runtime)
    runtime.command(
        "MODEL_START",
        {**runtime.identity("root"), "upper_bound": 12000, "request_hash": "expensive"},
    )
    state = runtime.read()
    assert state["reason"] == "BUDGET_EXHAUSTED"
    assert state["spent"] + state["reserved"] <= 12000


def test_tool_permissions_are_not_expanded_by_worker(runtime):
    award(runtime)
    queue(
        runtime,
        {
            "kind": "tool",
            "tool": "convert",
            "arguments": {"value": 20, "from_unit": "mm", "to_unit": "cm"},
        },
    )
    result = runtime.command("ACTION", runtime.identity("root"))
    assert result["error"] == "TOOL_NOT_ALLOWED"
    assert runtime.read()["world"] == runtime.private["world"]


def test_guessed_unknown_agent_has_no_observation(runtime):
    before = copy.deepcopy(runtime.read()["views"])
    result = runtime.command(
        "DISCOVER", {"actor": "initiator", "target": "guessed", "op": "describe", "search": "root"}
    )
    assert result == {"error": "NOT_OBSERVABLE"}
    assert runtime.read()["views"] == before


def test_worker_view_excludes_private_solution_and_registry(runtime):
    award(runtime)
    view = runtime.worker_view("root")
    assert set(view) == {"goal", "capability", "inputs", "agent_id", "tools", "observations"}
    other = next(a for a in runtime.private["profiles"] if a != view["agent_id"])
    assert other not in canonical_json(view)


def test_operational_acceptance_does_not_imply_goal_success(runtime):
    class Liar:
        def decide(self, view):
            return {"kind": "submit", "result": {"done": True}}

    result = run_episode(runtime, Liar())
    assert result["operational_accept"]
    assert not result["goal_correct"]
    assert not result["success"]


def test_worker_failure_is_a_recorded_unknown_call(runtime):
    class Broken:
        def decide(self, view):
            raise TimeoutError("provider timeout")

    result = run_episode(runtime, Broken())
    assert result["reason"] == "UNKNOWN_MODEL_CALL"
    assert result["reserved"] > 0


def test_all_fixture_episodes_execute_and_resume_without_changes(tmp_path):
    config = load_campaign(EXAMPLE)
    root = tmp_path / "campaign"
    result = run_campaign(config, root)
    assert result["episode_count"] == result["success_count"] == 72
    before = {p.name: p.read_bytes() for p in root.glob("*.jsonl")}
    assert run_campaign(config, root, resume=True) == result
    assert before == {p.name: p.read_bytes() for p in root.glob("*.jsonl")}
    other = tmp_path / "replication"
    assert run_campaign(config, other) == result
    assert before == {p.name: p.read_bytes() for p in other.glob("*.jsonl")}
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert any(e["kind"] == "RESUME_PARENT" for e in events)
    assert any(e["kind"] == "REFERRAL_DELIVERED" for e in events)


def test_campaign_budget_keeps_unexecuted_episodes_in_denominator(tmp_path):
    config = load_campaign(EXAMPLE)
    config["budget"]["campaign_limit"] = 12000
    root = tmp_path / "capped"
    result = run_campaign(config, root)
    assert result["episode_count"] == 72
    assert result["spent"] + result["reserved"] <= 12000
    rows = [json.loads(line) for line in (root / "episodes.jsonl").read_text().splitlines()]
    assert any(r["status"] == "NOT_RUN" and not r["success"] for r in rows)


def test_live_transport_sends_only_view_and_records_usage(monkeypatch):
    monkeypatch.setenv("TEST_MODEL_KEY", "private-test-value")

    class Transport:
        def open(self, request, timeout):
            sent = json.loads(request.data)
            assert sent["max_completion_tokens"] == 256
            assert request.get_header("Authorization") == "Bearer private-test-value"
            assert timeout == 10
            return io.BytesIO(
                json.dumps(
                    {
                        "id": "response-1",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": '{"kind":"submit","result":{"done":true}}'},
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 50,
                            "completion_tokens": 20,
                            "completion_tokens_details": {"reasoning_tokens": 5},
                        },
                    }
                ).encode()
            )

    worker = ChatWorker(
        {
            "base_url": "https://provider.example/v1",
            "model": "test-model",
            "api_key_env": "TEST_MODEL_KEY",
            "max_completion_tokens": 256,
            "timeout_seconds": 10,
            "credits_per_call": 500,
        },
        opener=Transport(),
    )
    reply = worker.decide({"goal": "test", "tools": {}, "observations": []})
    assert reply.usage["completion_tokens"] == 20
    assert reply.action["kind"] == "submit"
    assert "private-test-value" not in canonical_json(worker.manifest())


def test_tool_commit_at_exact_lease_expiry_is_rejected(runtime):
    runtime.config["execution"]["lease_ticks"] = 7
    award(runtime)
    identity = runtime.identity("root")
    queue(runtime, update_action())
    assert runtime.command("ACTION", identity)["error"] == "STALE_ATTEMPT"
    assert runtime.read()["world"]["revision"] == 0
    assert runtime.read()["effects"] == {}


def test_worker_outage_after_submission_does_not_discard_result(runtime):
    award(runtime)
    queue(runtime, update_action())
    runtime.command("ACTION", runtime.identity("root"))
    queue(runtime, {"kind": "submit", "result": {"done": True}})
    identity = runtime.identity("root")
    runtime.command("ACTION", identity)
    now = runtime.read()["clock"]
    runtime.private["faults"].append(
        {"agent_id": identity["agent_id"], "down": now + 1, "up": now + 10}
    )
    assert runtime.command("VERIFY", {"task_id": "root"})["passed"]
    assert runtime.read()["tasks"]["root"]["status"] == "ACCEPTED"


def test_parallel_calls_for_one_attempt_are_rejected(runtime):
    award(runtime)
    data = {**runtime.identity("root"), "upper_bound": 100, "request_hash": "same"}
    runtime.command("MODEL_START", data)
    with pytest.raises(ExecutionError, match="MODEL_CALL_ALREADY_STARTED"):
        runtime.command("MODEL_START", data)
    assert runtime.read()["reserved"] == 100


def test_live_reply_runs_through_runtime_and_preserves_provider_usage(runtime, monkeypatch):
    from tweetflows.workers import FixtureWorker

    monkeypatch.setenv("TEST_MODEL_KEY", "private-test-value")

    class ReactiveTransport:
        calls = 0

        def open(self, request, timeout):
            self.calls += 1
            view = json.loads(json.loads(request.data)["messages"][1]["content"])
            action = FixtureWorker().decide(view)
            return io.BytesIO(
                json.dumps(
                    {
                        "id": f"r-{self.calls}",
                        "choices": [
                            {"finish_reason": "stop", "message": {"content": json.dumps(action)}}
                        ],
                        "usage": {"prompt_tokens": 50, "completion_tokens": 40},
                    }
                ).encode()
            )

    worker = ChatWorker(
        {
            "base_url": "https://provider.example/v1",
            "model": "test-model",
            "api_key_env": "TEST_MODEL_KEY",
            "max_completion_tokens": 256,
            "timeout_seconds": 10,
            "credits_per_call": 500,
        },
        opener=ReactiveTransport(),
    )
    assert run_episode(runtime, worker)["success"]
    costs = [u for u in runtime.read()["usage"] if u["action"] == "model_call"]
    assert all(u["amount"] == 500 and u["provider_usage"]["completion_tokens"] == 40 for u in costs)
    assert "private-test-value" not in canonical_json(runtime.store.events())


def test_cost_contract_violation_stops_campaign(tmp_path):
    class OversizedReply:
        calls = 0

        def decide(self, view):
            self.calls += 1
            return {"kind": "submit", "result": {"done": True, "extra": "x" * 5000}}

    worker = OversizedReply()
    root = tmp_path / "contract"
    result = run_campaign(load_campaign(EXAMPLE), root, worker=worker)
    assert worker.calls == 1
    assert result["episode_count"] == 72
    rows = [json.loads(line) for line in (root / "episodes.jsonl").read_text().splitlines()]
    assert all(row["reason"] == "COST_CONTRACT_VIOLATION" for row in rows)
    assert not any(row["success"] for row in rows)


def test_non_integer_conversion_is_not_silently_rounded():
    from tweetflows.fixtures import prepare

    with pytest.raises(ExecutionError, match="NON_INTEGER_CONVERSION"):
        prepare({}, "convert", {"value": 25, "from_unit": "mm", "to_unit": "cm"})


def test_correct_goal_with_unwanted_change_is_not_success(runtime):
    class SideEffectWorker:
        def decide(self, view):
            if len(view["observations"]) == 0:
                return {
                    "kind": "tool",
                    "tool": "update_record",
                    "arguments": {"record_id": "order-2", "value": 99, "unit": "mm"},
                }
            if len(view["observations"]) == 1:
                return update_action()
            return {"kind": "submit", "result": {"done": True}}

    result = run_episode(runtime, SideEffectWorker())
    assert result["goal_correct"]
    assert not result["no_forbidden_effect"]
    assert not result["success"]
