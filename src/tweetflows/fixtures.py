"""Private fixture construction and controlled tools, never handed to a worker wholesale."""

import copy
import random

from tweetflows.config import digest
from tweetflows.store import ExecutionError

TOOLS = {
    "read_record": {"record_id": "string"},
    "update_record": {"record_id": "string", "value": "integer", "unit": "string"},
    "convert": {"value": "integer", "from_unit": "string", "to_unit": "string"},
}


def scenario(episode: dict) -> dict:
    seed = episode["seed_bundle"]["scenario"]
    ids = ["a-" + digest([seed, i])[:16] for i in range(8)]
    capabilities = [
        "records",
        "analysis",
        "conversion",
        "records",
        "analysis",
        "conversion",
        "records",
        "analysis",
    ]
    permissions = {
        "records": ["read_record", "update_record"],
        "analysis": ["read_record"],
        "conversion": ["convert"],
    }
    profiles = {
        aid: {
            "agent_id": aid,
            "version": 1,
            "capabilities": [cap],
            "subscription": cap,
            "tools": permissions[cap],
            "expertise": 0.5,
            "sociability": 0.5,
        }
        for aid, cap in zip(ids, capabilities, strict=True)
    }
    graph = {}
    rng = random.Random(episode["seed_bundle"]["topology"])
    for i, aid in enumerate(ids):
        neighbors = [ids[(i + 1) % 8], ids[(i + 2) % 8]]
        rng.shuffle(neighbors)
        graph[aid] = neighbors
    late = episode["task_instance_id"] == "late_conversion"
    world = {
        "records": {
            "order-1": {"value": 10, "unit": "cm" if late else "mm"},
            "order-2": {"value": 5, "unit": "mm"},
        },
        "revision": 0,
    }
    return {
        "profiles": profiles,
        "graph": graph,
        "initial_ids": ids[:2],
        "world": world,
        "goal": "Set order-1 to 20 mm. Preserve all other records.",
        "faults": (
            [{"agent_id": ids[0], "down": 4, "up": 18}]
            if episode["availability"] == "churn"
            else []
        ),
    }


def available(private: dict, agent_id: str, tick: int) -> bool:
    return not any(
        f["agent_id"] == agent_id and f["down"] <= tick < f["up"] for f in private["faults"]
    )


def interrupted(private: dict, agent_id: str, start: int, end: int) -> bool:
    return not available(private, agent_id, start) or any(
        f["agent_id"] == agent_id and start < f["down"] <= end for f in private["faults"]
    )


def prepare(world: dict, tool: str, args: dict) -> tuple[dict, dict]:
    expected = TOOLS.get(tool)
    if expected is None or set(args) != set(expected):
        raise ExecutionError("INVALID_TOOL_ARGUMENTS")
    for key, kind in expected.items():
        if (kind == "integer" and type(args[key]) is not int) or (
            kind == "string" and not isinstance(args[key], str)
        ):
            raise ExecutionError("INVALID_TOOL_ARGUMENTS")
    changed = copy.deepcopy(world)
    if tool == "convert":
        factors = {("cm", "mm"): (10, 1), ("mm", "mm"): (1, 1), ("mm", "cm"): (1, 10)}
        factor = factors.get((args["from_unit"], args["to_unit"]))
        if factor is None:
            raise ExecutionError("UNSUPPORTED_CONVERSION")
        numerator, denominator = factor
        if (args["value"] * numerator) % denominator:
            raise ExecutionError("NON_INTEGER_CONVERSION")
        return changed, {"value": args["value"] * numerator // denominator, "unit": args["to_unit"]}
    record = world["records"].get(args["record_id"])
    if record is None:
        raise ExecutionError("RECORD_NOT_FOUND")
    if tool == "read_record":
        return changed, copy.deepcopy(record)
    if args["unit"] != record["unit"]:
        return changed, {
            "error": "NEED_CONVERSION",
            "value": args["value"],
            "from_unit": args["unit"],
            "to_unit": record["unit"],
        }
    changed["records"][args["record_id"]]["value"] = args["value"]
    changed["revision"] += 1
    return changed, {
        "updated": True,
        "record": copy.deepcopy(changed["records"][args["record_id"]]),
    }


def grade(initial: dict, final: dict, root: dict) -> dict:
    """Private end-state evaluation; never exposed in a worker view."""
    record = final["records"]["order-1"]
    target = 2 if initial["records"]["order-1"]["unit"] == "cm" else 20
    goal_correct = record == {"value": target, "unit": initial["records"]["order-1"]["unit"]}
    other_correct = final["records"]["order-2"] == initial["records"]["order-2"]
    return {
        "goal_correct": goal_correct,
        "no_forbidden_effect": other_correct,
        "operational_accept": root["status"] == "ACCEPTED",
        "evaluation_complete": True,
    }
