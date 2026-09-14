"""Transactional fixture execution with epoch fencing and a shared root budget."""

import copy
from pathlib import Path

from tweetflows.config import digest
from tweetflows.fixtures import TOOLS, available, interrupted, prepare
from tweetflows.store import ExecutionError, Store
from tweetflows.workers import validate_action

TERMINAL = {"ACCEPTED", "FAILED", "CANCELED"}


def task(task_id, capability, inputs=None, parent=None):
    return {
        "task_id": task_id,
        "capability": capability,
        "inputs": inputs or {},
        "parent": parent,
        "status": "OPEN",
        "epoch": 0,
        "input_version": 1,
        "attempt": None,
        "attempts": 0,
        "observations": [],
        "pending": None,
        "children": [],
        "result": None,
    }


class Runtime:
    def __init__(self, path: Path, config: dict, episode: dict, private: dict):
        self.config, self.episode, self.private = config, episode, private
        profiles = private["profiles"]
        prior = config["reputation"]
        neutral = prior["prior_successes"] / (prior["prior_successes"] + prior["prior_failures"])
        for profile in profiles.values():
            profile["expertise"] = profile["sociability"] = neutral
        seeds = list(profiles) if episode["visibility"] == "full" else private["initial_ids"]
        views = {
            "initiator": {
                "known": {a: 0 for a in seeds},
                "profiles": {a: {**profiles[a], "observed_at": 0} for a in seeds},
            }
        }
        for aid, profile in profiles.items():
            views[aid] = {
                "known": dict.fromkeys([aid, *private["graph"][aid]], 0),
                "profiles": {aid: {**profile, "observed_at": 0}},
            }
        initial = {
            "schema_version": "1.0",
            "episode_id": episode["episode_id"],
            "config_hash": digest(config),
            "scenario_hash": digest(private),
            "serial": 0,
            "clock": 0,
            "world": copy.deepcopy(private["world"]),
            "tasks": {"root": task("root", "records")},
            "attempts": {},
            "views": views,
            "spent": 0,
            "reserved": 0,
            "reservations": {},
            "usage": [],
            "effects": {},
            "offers": {},
            "search_contacts": {},
            "search_depths": {},
            "contacts": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "reason": None,
        }
        self.store = Store(path, initial)
        actual = self.store.read()
        if actual["config_hash"] != digest(config) or actual["scenario_hash"] != digest(private):
            self.store.close()
            raise ExecutionError("RESUME_CONFIG_MISMATCH")

    def read(self):
        return self.store.read()

    def emit(self, state, events, kind, **payload):
        events.append({"kind": kind, "sim_time": state["clock"], **payload})

    def _fail(self, state, events, reason):
        state["reason"] = state["reason"] or reason
        for current in state["tasks"].values():
            if current["status"] not in TERMINAL:
                current["status"] = "FAILED"
                if current["attempt"]:
                    state["attempts"][current["attempt"]]["status"] = "FAILED"
        self.emit(state, events, "EPISODE_FAILED", reason=state["reason"])

    def _retry(self, state, events, current, reason):
        if current["attempt"]:
            state["attempts"][current["attempt"]]["status"] = "EXPIRED"
        current["pending"] = None
        current["attempt"] = None
        current["status"] = (
            "OPEN"
            if current["attempts"] < self.config["execution"]["max_attempts_per_task"]
            else "FAILED"
        )
        if current["status"] == "FAILED":
            self._fail(state, events, reason)
        self.emit(state, events, "ATTEMPT_ENDED", task_id=current["task_id"], reason=reason)

    def _tick(self, state, events, duration):
        start = state["clock"]
        state["clock"] += duration
        for fault in self.private["faults"]:
            for key in ("down", "up"):
                if start < fault[key] <= state["clock"]:
                    events.append(
                        {
                            "kind": "AGENT_" + key.upper(),
                            "sim_time": fault[key],
                            "agent_id": fault["agent_id"],
                        }
                    )
        if state["clock"] >= self.config["execution"]["root_deadline_ticks"]:
            self._fail(state, events, "DEADLINE_EXCEEDED")
            return
        for current in list(state["tasks"].values()):
            if current["status"] not in {"ASSIGNED", "RUNNING"}:
                continue
            attempt = state["attempts"][current["attempt"]]
            if interrupted(self.private, attempt["agent_id"], start, state["clock"]):
                self._retry(state, events, current, "AGENT_UNAVAILABLE")
            elif state["clock"] >= attempt["expires_at"]:
                self._retry(state, events, current, "LEASE_EXPIRED")

    def _charge(self, state, events, amount, phase, action):
        if state["spent"] + state["reserved"] + amount > self.config["budget"]["per_episode_limit"]:
            self._fail(state, events, "BUDGET_EXHAUSTED")
            return False
        state["spent"] += amount
        state["usage"].append(
            {
                "id": f"u-{len(state['usage']) + 1}",
                "action": action,
                "phase": phase,
                "amount": amount,
                "status": "SETTLED",
            }
        )
        return True

    def _current(self, state, data):
        current = state["tasks"].get(data["task_id"])
        if current is None or current["status"] != "RUNNING":
            raise ExecutionError("STALE_ATTEMPT")
        attempt = state["attempts"][current["attempt"]]
        if any(data[key] != attempt[key] for key in ("agent_id", "epoch", "input_version")):
            raise ExecutionError("STALE_ATTEMPT")
        if data["attempt_id"] != current["attempt"]:
            raise ExecutionError("STALE_ATTEMPT")
        return current

    def command(self, kind, data, command_id=None):
        command_id = command_id or f"c-{self.read()['serial'] + 1}"

        def change(state, events):
            state["serial"] += 1
            response = self._dispatch(state, events, kind, data)
            self.emit(state, events, kind, request=data, response=response)
            return response

        return self.store.apply(command_id, {"kind": kind, **data}, change)

    def _dispatch(self, state, events, kind, data):
        if kind == "FAIL":
            self._fail(state, events, data["reason"])
            return {"ok": False}
        if kind == "RECOVER":
            uncertain = [r for r in state["reservations"].values() if r["status"] == "STARTED"]
            for reservation in uncertain:
                reservation["status"] = "UNKNOWN"
            if uncertain:
                self._fail(state, events, "UNKNOWN_MODEL_CALL")
            return {"unknown_calls": len(uncertain)}
        if kind == "DISCOVER":
            return self._discover(state, events, data)
        if kind == "AWARD":
            current = state["tasks"][data["task_id"]]
            offer = state["offers"].get(data["offer_id"])
            if (
                current["status"] != "OPEN"
                or offer is None
                or offer["task_id"] != data["task_id"]
                or offer["input_version"] != current["input_version"]
                or offer["expires_at"] <= state["clock"]
                or not available(self.private, offer["agent_id"], state["clock"])
            ):
                return {"error": "INVALID_AWARD"}
            current["epoch"] += 1
            current["attempts"] += 1
            attempt_id = f"{current['task_id']}-a{current['epoch']}"
            attempt = {
                "attempt_id": attempt_id,
                "agent_id": offer["agent_id"],
                "epoch": current["epoch"],
                "input_version": current["input_version"],
                "expires_at": state["clock"] + self.config["execution"]["lease_ticks"],
                "status": "RUNNING",
            }
            state["attempts"][attempt_id] = attempt
            current.update(status="RUNNING", attempt=attempt_id)
            return {"ok": True, **attempt}
        if kind == "MODEL_START":
            current = self._current(state, data)
            if current["pending"] is not None:
                raise ExecutionError("ACTION_ALREADY_PENDING")
            if any(
                r["status"] == "STARTED" and r["identity"]["attempt_id"] == data["attempt_id"]
                for r in state["reservations"].values()
            ):
                raise ExecutionError("MODEL_CALL_ALREADY_STARTED")
            amount = data["upper_bound"]
            if type(amount) is not int or amount < 0:
                raise ExecutionError("INVALID_RESERVATION")
            if (
                state["model_calls"] >= self.config["budget"]["max_model_calls_per_episode"]
                or state["spent"] + state["reserved"] + amount
                > self.config["budget"]["per_episode_limit"]
            ):
                self._fail(state, events, "BUDGET_EXHAUSTED")
                return {"error": "BUDGET_EXHAUSTED"}
            call_id = f"model-{state['model_calls'] + 1}"
            state["model_calls"] += 1
            state["reserved"] += amount
            state["reservations"][call_id] = {
                "status": "STARTED",
                "amount": amount,
                "request_hash": data["request_hash"],
                "identity": {
                    k: data[k]
                    for k in ("agent_id", "attempt_id", "epoch", "input_version", "task_id")
                },
            }
            return {"call_id": call_id}
        if kind == "MODEL_FINISH":
            reservation = state["reservations"][data["call_id"]]
            if reservation["status"] != "STARTED":
                raise ExecutionError("CALL_ALREADY_SETTLED")
            if any(data[k] != v for k, v in reservation["identity"].items()):
                raise ExecutionError("CALL_IDENTITY_MISMATCH")
            actual = data["cost"]
            if type(actual) is not int or actual < 0 or actual > reservation["amount"]:
                reservation["status"] = "UNKNOWN"
                self._fail(state, events, "COST_CONTRACT_VIOLATION")
                return {"error": "COST_CONTRACT_VIOLATION"}
            state["reserved"] -= reservation["amount"]
            state["spent"] += actual
            reservation.update(status="SETTLED", actual=actual)
            state["usage"].append(
                {
                    "id": data["call_id"],
                    "action": "model_call",
                    "phase": "EXECUTION",
                    "provider_usage": data.get("usage", {}),
                    "response_id": data.get("response_id"),
                    "amount": actual,
                    "status": "SETTLED",
                }
            )
            self._tick(state, events, self.config["time_model"]["duration_ticks"]["model_call"])
            try:
                current = self._current(state, data)
                current["pending"] = validate_action(data["action"])
            except ExecutionError as exc:
                return {"error": str(exc)}
            return {"ok": True}
        if kind == "ACTION":
            current = self._current(state, data)
            action = current["pending"]
            if action is None:
                raise ExecutionError("NO_PENDING_ACTION")
            current["pending"] = None
            if action["kind"] == "tool":
                return self._tool(state, events, current, data, action)
            if action["kind"] == "need":
                return self._need(state, events, current, action)
            current.update(status="SUBMITTED", result=action["result"])
            state["attempts"][current["attempt"]]["status"] = "SUBMITTED"
            return {"ok": True}
        if kind == "VERIFY":
            current = state["tasks"][data["task_id"]]
            if current["status"] != "SUBMITTED":
                raise ExecutionError("INVALID_STATE")
            current["status"] = "VERIFYING"
            if not self._charge(
                state,
                events,
                self.config["budget"]["tariff"]["operational_verification"],
                "OPERATIONAL_VERIFY",
                "verify",
            ):
                return {"error": "BUDGET_EXHAUSTED"}
            self._tick(
                state,
                events,
                self.config["time_model"]["duration_ticks"]["operational_verification"],
            )
            if current["status"] == "FAILED":
                return {"error": state["reason"]}
            result = current["result"]
            passed = (
                type(result.get("value")) is int and isinstance(result.get("unit"), str)
                if current["capability"] == "conversion"
                else result.get("done") is True
            )
            if passed:
                current["status"] = "ACCEPTED"
                state["attempts"][current["attempt"]]["status"] = "SUCCEEDED"
            else:
                self._retry(state, events, current, "VERIFICATION_FAILED")
            return {"passed": passed}
        if kind == "RESUME_PARENT":
            current = state["tasks"][data["task_id"]]
            if current["status"] != "WAITING":
                raise ExecutionError("INVALID_STATE")
            children = [state["tasks"][tid] for tid in current["children"]]
            if not all(child["status"] == "ACCEPTED" for child in children):
                raise ExecutionError("DEPENDENCY_PENDING")
            current["observations"].append({"child_result": children[-1]["result"]})
            attempt = state["attempts"][current["attempt"]]
            if not available(self.private, attempt["agent_id"], state["clock"]):
                self._retry(state, events, current, "AGENT_UNAVAILABLE")
            else:
                current["status"] = attempt["status"] = "RUNNING"
                attempt["expires_at"] = state["clock"] + attempt["remaining_lease"]
            return {"ok": True}
        if kind == "INVALIDATE_INPUT":
            current = state["tasks"][data["task_id"]]
            if current["status"] in TERMINAL:
                raise ExecutionError("TERMINAL_TASK")
            current["input_version"] += 1
            self._retry(state, events, current, "INPUT_CHANGED")
            current["observations"] = []
            for child_id in current["children"]:
                child = state["tasks"][child_id]
                child["invalidated"] = True
                if child["status"] not in TERMINAL:
                    child["status"] = "CANCELED"
                    if child["attempt"]:
                        state["attempts"][child["attempt"]]["status"] = "CANCELED"
            current["children"] = []
            return {"ok": True}
        raise ExecutionError("UNKNOWN_COMMAND")

    def _discover(self, state, events, data):
        actor, target, op = data["actor"], data["target"], data["op"]
        view = state["views"].get(actor)
        if view is None or target not in view["known"]:
            return {"error": "NOT_OBSERVABLE"}
        search = data["search"]
        depths = state["search_depths"].setdefault(
            search, dict.fromkeys(state["views"]["initiator"]["profiles"], 0)
        )
        if actor != "initiator" and actor in depths and target in self.private["graph"][actor]:
            candidate_depth = depths[actor] + 1
            depths[target] = min(depths.get(target, candidate_depth), candidate_depth)
        limits = self.config["discovery"]
        if target not in depths or depths[target] > limits["max_hops_from_search_seed"]:
            return {"error": "HOP_LIMIT"}
        if (
            state["contacts"] >= limits["max_contacts_per_root"]
            or state["search_contacts"].get(search, 0) >= limits["max_contacts_per_search"]
        ):
            return {"error": "DISCOVERY_EXHAUSTED"}
        state["contacts"] += 1
        state["search_contacts"][search] = state["search_contacts"].get(search, 0) + 1
        if not self._charge(state, events, self.config["budget"]["tariff"][op], "DISCOVERY", op):
            return {"error": "BUDGET_EXHAUSTED"}
        start = state["clock"]
        self._tick(state, events, self.config["time_model"]["duration_ticks"][op])
        if state["reason"]:
            return {"error": state["reason"]}
        if interrupted(self.private, target, start, state["clock"]):
            return {"error": "AGENT_UNAVAILABLE"}
        profile = self.private["profiles"][target]
        if op == "describe":
            observation = {**profile, "observed_at": state["clock"]}
            view["profiles"][target] = observation
            return {"profile": observation}
        if op == "probe":
            return {"available": True}
        if op == "contacts":
            offset = data.get("offset", 0)
            page = self.private["graph"][target][
                offset : offset + self.config["visibility"]["contacts_page_size"]
            ]
            for aid in page:
                depth = depths[target] + 1
                depths[aid] = min(depths.get(aid, depth), depth)
                view["known"].setdefault(aid, depth)
            return {"contacts": page, "next_offset": offset + len(page) if page else None}
        if op == "referral_forward":
            # Only the explicit message is delivered; the recipient keeps its own local view.
            self.emit(
                state,
                events,
                "REFERRAL_DELIVERED",
                sender=actor,
                recipient=target,
                search=search,
                capability=data["capability"],
            )
            return {"delivered": True}
        if op == "offer_request":
            current = state["tasks"][data["task_id"]]
            if current["capability"] not in profile["capabilities"]:
                return {"error": "DECLINED"}
            offer_id = "offer-" + digest([search, target, state["serial"]])[:20]
            state["offers"][offer_id] = {
                "agent_id": target,
                "task_id": current["task_id"],
                "input_version": current["input_version"],
                "expires_at": state["clock"] + 5,
            }
            return {"offer_id": offer_id}
        raise ExecutionError("INVALID_DISCOVERY_OPERATION")

    def _tool(self, state, events, current, data, action):
        name, args = action["tool"], action["arguments"]
        if name not in self.private["profiles"][data["agent_id"]]["tools"]:
            self._retry(state, events, current, "TOOL_NOT_ALLOWED")
            return {"error": "TOOL_NOT_ALLOWED"}
        if state["tool_calls"] >= self.config["budget"]["max_total_tool_calls_per_episode"]:
            self._fail(state, events, "TOOL_LIMIT")
            return {"error": "TOOL_LIMIT"}
        state["tool_calls"] += 1
        if not self._charge(
            state, events, self.config["budget"]["tariff"]["sandbox_tool"], "EXECUTION", name
        ):
            return {"error": "BUDGET_EXHAUSTED"}
        key = digest(["root", current["input_version"], name, args])
        self._tick(state, events, self.config["time_model"]["duration_ticks"]["sandbox_tool"])
        try:
            self._current(state, data)
        except ExecutionError:
            return {"error": "STALE_ATTEMPT"}
        if key in state["effects"]:
            result = state["effects"][key]["result"]
        else:
            try:
                changed, result = prepare(state["world"], name, args)
            except ExecutionError as exc:
                result = {"error": str(exc)}
                changed = state["world"]
            if changed != state["world"]:
                state["world"] = changed
                state["effects"][key] = {
                    "result": result,
                    "epoch": data["epoch"],
                    "revision": changed["revision"],
                    "task_id": current["task_id"],
                }
                self.emit(
                    state, events, "EFFECT_COMMITTED", effect_key=key, revision=changed["revision"]
                )
        current["observations"].append(result)
        return result

    def _need(self, state, events, current, action):
        last = current["observations"][-1] if current["observations"] else {}
        expected = {k: last.get(k) for k in ("value", "from_unit", "to_unit")}
        if last.get("error") != "NEED_CONVERSION" or action["inputs"] != expected:
            self._retry(state, events, current, "UNSUPPORTED_REQUIREMENT")
            return {"error": "UNSUPPORTED_REQUIREMENT"}
        if current["parent"] is not None or self.config["execution"]["max_child_depth"] < 1:
            self._fail(state, events, "DEPENDENCY_DEPTH")
            return {"error": "DEPENDENCY_DEPTH"}
        child_id = (
            "child-" + digest([current["task_id"], current["input_version"], action["inputs"]])[:16]
        )
        if child_id not in state["tasks"]:
            if len(state["tasks"]) >= self.config["execution"]["max_tasks_per_root"]:
                self._fail(state, events, "TASK_LIMIT")
                return {"error": "TASK_LIMIT"}
            state["tasks"][child_id] = task(
                child_id, "conversion", action["inputs"], current["task_id"]
            )
        if child_id not in current["children"]:
            current["children"].append(child_id)
        current["status"] = "WAITING"
        attempt = state["attempts"][current["attempt"]]
        attempt["status"] = "SUSPENDED"
        attempt["remaining_lease"] = attempt["expires_at"] - state["clock"]
        return {"child_id": child_id}

    def worker_view(self, task_id):
        state = self.read()
        current = state["tasks"][task_id]
        attempt = state["attempts"][current["attempt"]]
        allowed = self.private["profiles"][attempt["agent_id"]]["tools"]
        return {
            "goal": self.private["goal"]
            if current["parent"] is None
            else "Convert the given value.",
            "capability": current["capability"],
            "inputs": current["inputs"],
            "agent_id": attempt["agent_id"],
            "tools": {name: TOOLS[name] for name in allowed},
            "observations": current["observations"],
        }

    def identity(self, task_id):
        state = self.read()
        current = state["tasks"][task_id]
        attempt = state["attempts"][current["attempt"]]
        return {
            "task_id": task_id,
            **{k: attempt[k] for k in ("agent_id", "attempt_id", "epoch", "input_version")},
        }

    def close(self):
        self.store.close()
