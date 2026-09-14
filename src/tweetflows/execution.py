"""Campaign and episode execution with persistent results and separate private grading."""

import json
import sqlite3
from pathlib import Path

from tweetflows.config import canonical_json, digest, validate_campaign
from tweetflows.fixtures import grade, scenario
from tweetflows.live import ChatWorker, ModelReply
from tweetflows.planning import plan_campaign
from tweetflows.routing import port_for, select_agent
from tweetflows.runtime import TERMINAL, Runtime
from tweetflows.store import ExecutionError
from tweetflows.workers import FixtureWorker


def run_episode(runtime: Runtime, worker=None, step_limit=1000):
    worker = worker or FixtureWorker()
    runtime.command("RECOVER", {})
    for _ in range(step_limit):
        state = runtime.read()
        if state["tasks"]["root"]["status"] in TERMINAL:
            break
        active = next(
            (
                t
                for t in state["tasks"].values()
                if t["status"] not in TERMINAL and t["status"] != "WAITING"
            ),
            None,
        )
        if active is None:
            waiting = next(t for t in state["tasks"].values() if t["status"] == "WAITING")
            runtime.command("RESUME_PARENT", {"task_id": waiting["task_id"]})
            continue
        task_id = active["task_id"]
        if active["status"] == "OPEN":
            offer = select_agent(
                port_for(runtime), task_id, active["capability"], runtime.episode["method_id"]
            )
            if offer is None:
                runtime.command("FAIL", {"reason": "DISCOVERY_EXHAUSTED"})
            else:
                runtime.command("AWARD", {"task_id": task_id, "offer_id": offer})
        elif active["status"] == "SUBMITTED":
            runtime.command("VERIFY", {"task_id": task_id})
        elif active["pending"] is not None:
            runtime.command("ACTION", runtime.identity(task_id))
        else:
            identity = runtime.identity(task_id)
            view = runtime.worker_view(task_id)
            # Fixture credits use UTF-8 byte counts as a conservative, documented unit.
            tariff = runtime.config["budget"]["tariff"]
            max_output = runtime.config["model"]["max_output_tokens"]
            upper = (
                tariff["model_call_fixed"]
                + len(canonical_json(view).encode()) * tariff["input_token"]
                + max_output * tariff["output_token_excluding_reasoning"]
            )
            if isinstance(worker, ChatWorker):
                upper = worker.settings["credits_per_call"]
            started = runtime.command(
                "MODEL_START", {**identity, "upper_bound": upper, "request_hash": digest(view)}
            )
            if "call_id" not in started:
                continue
            try:
                action = worker.decide(view)
            except Exception:
                # The provider may have received the request. Never silently resend it.
                runtime.command("RECOVER", {})
                break
            reply = action if isinstance(action, ModelReply) else None
            if reply is not None:
                action = reply.action
            actual = (
                tariff["model_call_fixed"]
                + len(canonical_json(view).encode()) * tariff["input_token"]
                + len(canonical_json(action).encode()) * tariff["output_token_excluding_reasoning"]
            )
            if reply is not None:
                actual = upper
            runtime.command(
                "MODEL_FINISH",
                {
                    **identity,
                    "call_id": started["call_id"],
                    "action": action,
                    "cost": actual,
                    "usage": reply.usage if reply else {},
                    "provider_request_hash": reply.request_hash if reply else None,
                    "response_id": reply.response_id if reply else None,
                },
            )
    else:
        runtime.command("FAIL", {"reason": "STEP_LIMIT"})
    state = runtime.read()
    result = grade(runtime.private["world"], state["world"], state["tasks"]["root"])
    within_budget = (
        state["spent"] + state["reserved"] <= runtime.config["budget"]["per_episode_limit"]
    )
    within_deadline = state["clock"] < runtime.config["execution"]["root_deadline_ticks"]
    complete = not any(
        r["status"] in {"STARTED", "UNKNOWN"} for r in state["reservations"].values()
    )
    return {
        **runtime.episode,
        **result,
        "status": state["tasks"]["root"]["status"],
        "reason": state["reason"],
        "within_budget": within_budget,
        "within_deadline": within_deadline,
        "evaluation_complete": complete,
        "spent": state["spent"],
        "reserved": state["reserved"],
        "sim_time": state["clock"],
        "model_calls": state["model_calls"],
        "contacts": state["contacts"],
        "world_hash": digest(state["world"]),
        "success": result["goal_correct"]
        and result["no_forbidden_effect"]
        and within_budget
        and within_deadline
        and complete,
    }


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _run_campaign(value, directory: Path, resume=False, worker=None):
    config = validate_campaign(value)
    if isinstance(worker, ChatWorker) and config["planning"]["expected_episodes"] > 12:
        raise ExecutionError("LIVE_SMOKE_LIMIT: select at most 12 episodes")
    plan = plan_campaign(config)
    worker_manifest = worker.manifest() if isinstance(worker, ChatWorker) else {"kind": "fixture"}
    plan["execution_worker"] = worker_manifest
    plan["execution_source_hash"] = execution_source_hash()
    execution_identity = digest(
        {"source": plan["execution_source_hash"], "worker": worker_manifest}
    )
    for episode in plan["episodes"]:
        episode["infrastructure_hash"] = digest(
            [episode["infrastructure_hash"], execution_identity]
        )
        episode["pair_id"] = "pair-" + digest([episode["pair_id"], execution_identity])
        episode["episode_id"] = "ep-" + digest([episode["pair_id"], episode["method_id"]])
        episode["mode"] = "live" if isinstance(worker, ChatWorker) else "fixture"
    plan["execution_profile"] = "engineering_smoke_v1"
    plan["execution_ready"] = True
    plan["study_ready"] = False
    plan["unresolved_execution_artifacts"] = []
    plan.pop("plan_hash")
    plan["plan_hash"] = digest(plan)
    if resume:
        saved = json.loads((directory / "run_plan.json").read_text())
        if saved != plan:
            raise ExecutionError("RESUME_CONFIG_MISMATCH")
    else:
        directory.mkdir(parents=True, exist_ok=False)
        _write_json(directory / "run_plan.json", plan)
    db = sqlite3.connect(directory / "campaign.sqlite", isolation_level=None)
    db.execute("PRAGMA synchronous=FULL")
    db.executescript("""CREATE TABLE IF NOT EXISTS episodes (
        id TEXT PRIMARY KEY, reserved INTEGER NOT NULL, result TEXT);
    """)
    results, all_events, usage = [], [], []
    halted = any(
        json.loads(row[0]).get("reason") == "COST_CONTRACT_VIOLATION"
        for row in db.execute("SELECT result FROM episodes WHERE result IS NOT NULL")
    )
    try:
        for episode in plan["episodes"]:
            episode_id = episode["episode_id"]
            row = db.execute(
                "SELECT reserved,result FROM episodes WHERE id=?", (episode_id,)
            ).fetchone()
            if row is None:
                db.execute("BEGIN IMMEDIATE")
                total = db.execute("SELECT COALESCE(SUM(reserved),0) FROM episodes").fetchone()[0]
                if (
                    halted
                    or total + config["budget"]["per_episode_limit"]
                    > config["budget"]["campaign_limit"]
                ):
                    result = {
                        **episode,
                        "status": "NOT_RUN",
                        "reason": "COST_CONTRACT_VIOLATION" if halted else "CAMPAIGN_BUDGET",
                        "success": False,
                        "evaluation_complete": False,
                        "spent": 0,
                        "reserved": 0,
                    }
                    db.execute(
                        "INSERT INTO episodes VALUES (?,0,?)", (episode_id, canonical_json(result))
                    )
                else:
                    db.execute(
                        "INSERT INTO episodes VALUES (?,?,NULL)",
                        (episode_id, config["budget"]["per_episode_limit"]),
                    )
                db.execute("COMMIT")
                row = db.execute(
                    "SELECT reserved,result FROM episodes WHERE id=?", (episode_id,)
                ).fetchone()
            if row[1] is not None:
                result = json.loads(row[1])
            else:
                private = scenario(episode)
                private["worker_manifest"] = worker_manifest
                runtime = Runtime(directory / f"{episode_id}.sqlite", config, episode, private)
                try:
                    result = run_episode(runtime, worker)
                finally:
                    runtime.close()
                db.execute(
                    "UPDATE episodes SET reserved=?,result=? WHERE id=?",
                    (result["spent"] + result["reserved"], canonical_json(result), episode_id),
                )
            if result.get("reason") == "COST_CONTRACT_VIOLATION":
                halted = True
            results.append(result)
            path = directory / f"{episode_id}.sqlite"
            if path.exists():
                runtime = Runtime(
                    path, config, episode, {**scenario(episode), "worker_manifest": worker_manifest}
                )
                try:
                    all_events.extend(
                        {"episode_id": episode_id, **event} for event in runtime.store.events()
                    )
                    usage.extend(
                        {"episode_id": episode_id, **entry} for entry in runtime.read()["usage"]
                    )
                finally:
                    runtime.close()
    finally:
        db.close()
    for filename, rows in (
        ("episodes.jsonl", results),
        ("events.jsonl", all_events),
        ("usage.jsonl", usage),
    ):
        (directory / filename).write_text("".join(canonical_json(row) + "\n" for row in rows))
    metrics = {
        "episode_count": len(results),
        "success_count": sum(r["success"] for r in results),
        "success_rate": sum(r["success"] for r in results) / len(results),
        "spent": sum(r["spent"] for r in results),
        "reserved": sum(r["reserved"] for r in results),
        "worker": type(worker or FixtureWorker()).__name__,
        "research_results": False,
    }
    _write_json(directory / "metrics.json", metrics)
    return metrics


def execution_source_hash():
    from importlib.resources import files

    root = files("tweetflows")
    return digest(
        {
            name: root.joinpath(name).read_text()
            for name in (
                "execution.py",
                "runtime.py",
                "routing.py",
                "fixtures.py",
                "store.py",
                "workers.py",
                "live.py",
            )
        }
    )


def run_campaign(value, directory: Path, resume=False, worker=None):
    import fcntl

    lock_path = directory.parent / (directory.name + ".lock")
    directory.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ExecutionError("CAMPAIGN_ALREADY_RUNNING") from exc
        try:
            return _run_campaign(value, directory, resume, worker)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
