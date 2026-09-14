"""Typed reactive worker boundary. Workers receive public views only."""

from typing import Protocol

from tweetflows.store import ExecutionError


class Worker(Protocol):
    def decide(self, view: dict) -> dict: ...


class FixtureWorker:
    """Deterministic protocol driver for fixtures; not an LLM or research result."""

    def decide(self, view: dict) -> dict:
        history = view["observations"]
        if view["capability"] == "conversion":
            if not history:
                return {"kind": "tool", "tool": "convert", "arguments": view["inputs"]}
            return {"kind": "submit", "result": history[-1]}
        if not history:
            return {
                "kind": "tool",
                "tool": "update_record",
                "arguments": {"record_id": "order-1", "value": 20, "unit": "mm"},
            }
        last = history[-1]
        if last.get("updated"):
            return {"kind": "submit", "result": {"done": True}}
        if last.get("error") == "NEED_CONVERSION":
            return {
                "kind": "need",
                "capability": "conversion",
                "inputs": {k: last[k] for k in ("value", "from_unit", "to_unit")},
            }
        if "child_result" in last:
            value = last["child_result"]
            return {
                "kind": "tool",
                "tool": "update_record",
                "arguments": {
                    "record_id": "order-1",
                    "value": value["value"],
                    "unit": value["unit"],
                },
            }
        # The request is 20 mm; a unit mismatch is learned only through a tool result.
        return {
            "kind": "tool",
            "tool": "update_record",
            "arguments": {"record_id": "order-1", "value": 20, "unit": "mm"},
        }


def validate_action(action: object) -> dict:
    if not isinstance(action, dict):
        raise ExecutionError("INVALID_ACTION")
    kind = action.get("kind")
    fields = {
        "tool": {"kind", "tool", "arguments"},
        "need": {"kind", "capability", "inputs"},
        "submit": {"kind", "result"},
    }
    if not isinstance(kind, str) or kind not in fields or set(action) != fields[kind]:
        raise ExecutionError("INVALID_ACTION")
    body = action[{"tool": "arguments", "need": "inputs", "submit": "result"}[kind]]
    if not isinstance(body, dict):
        raise ExecutionError("INVALID_ACTION")
    if kind == "tool" and not isinstance(action["tool"], str):
        raise ExecutionError("INVALID_ACTION")
    if kind == "need" and action["capability"] != "conversion":
        raise ExecutionError("INVALID_REQUIREMENT")
    return action
