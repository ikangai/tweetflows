"""Three discovery policies operating through paid, actor-scoped observations."""

import copy

from tweetflows.config import digest


class Discovery:
    """Public router port: no scenario, solution, or private registry attribute."""

    def __init__(self, view, request, config, seed):
        self.view = view
        self.request = request
        self.config = config
        self.seed = seed


def select_agent(port: Discovery, task_id: str, capability: str, method: str) -> str | None:
    limits = port.config["discovery"]
    visited = set()
    checked = set()
    search = f"{task_id}:{capability}"
    weights = limits["candidate_weights"]

    def request(actor, target, op, depth, **extra):
        return port.request(
            {
                "actor": actor,
                "target": target,
                "op": op,
                "search": search,
                "task_id": task_id,
                "capability": capability,
                "depth": depth,
                **extra,
            }
        )

    def score(profile, relay=False):
        selected = limits["relay_weights"] if relay else weights
        match = float(capability in profile["capabilities"])
        age = max(0, port.view("initiator")["clock"] - profile["observed_at"])
        fresh = max(0, 1 - age / limits["freshness_horizon_ticks"])
        history = "sociability" if relay else "expertise"
        return (
            selected["match"] * match
            + selected[history] * profile[history]
            + selected["freshness"] * fresh
        )

    def ranked(profiles, relay=False):
        return sorted(
            profiles, key=lambda p: (-score(p, relay), digest([port.seed, p["agent_id"]]))
        )

    def direct(actor, depth):
        for profile in ranked(list(port.view(actor)["profiles"].values())):
            aid = profile["agent_id"]
            matches = (
                capability == profile["subscription"]
                if method == "intent_local_v1"
                else capability in profile["capabilities"]
            )
            if aid in checked or not matches:
                continue
            checked.add(aid)
            if not request(actor, aid, "probe", depth).get("available"):
                continue
            offer = request(actor, aid, "offer_request", depth)
            if "offer_id" in offer:
                return offer["offer_id"]
        return None

    def expand(actor, target, depth):
        offset = 0
        while depth < limits["max_hops_from_search_seed"]:
            reply = request(actor, target, "contacts", depth, offset=offset)
            for aid in reply.get("contacts", []):
                if aid not in port.view(actor)["profiles"]:
                    request(actor, aid, "describe", depth + 1)
            next_offset = reply.get("next_offset")
            if next_offset is None or next_offset == offset:
                break
            # Each actor's fixture graph has two neighbors; no empty terminal page is needed.
            if len(reply.get("contacts", [])) < port.config["visibility"]["contacts_page_size"]:
                break
            offset = next_offset
            if offset >= 2:
                break

    def central(actor="initiator"):
        while True:
            found = direct(actor, 0)
            if found:
                return found
            view = port.view(actor)
            frontier = [
                p
                for p in view["profiles"].values()
                if p["agent_id"] not in visited
                and view["known"][p["agent_id"]] < limits["max_hops_from_search_seed"]
            ]
            if not frontier:
                return None
            profile = ranked(frontier, relay=True)[0]
            aid = profile["agent_id"]
            visited.add(aid)
            expand(actor, aid, view["known"][aid])

    def referral(actor, depth):
        found = direct(actor, depth)
        if found:
            return found
        if depth >= limits["max_hops_from_search_seed"]:
            return None
        view = port.view(actor)
        for aid in view["known"]:
            if aid not in view["profiles"]:
                request(actor, aid, "describe", depth)
        candidates = [
            p for p in port.view(actor)["profiles"].values() if p["agent_id"] not in visited
        ]
        for start in range(0, len(candidates), limits["referral_fanout"]):
            wave = ranked(candidates, relay=True)[start : start + limits["referral_fanout"]]
            for profile in wave:
                aid = profile["agent_id"]
                visited.add(aid)
                if request(actor, aid, "referral_forward", depth).get("delivered"):
                    found = referral(aid, depth + 1)
                    if found:
                        return found
        return None

    if method == "central_active_v1":
        return central()
    if method == "intent_local_v1":
        brokers = [("initiator", 0)]
        while brokers:
            actor, depth = brokers.pop(0)
            found = direct(actor, depth)
            if found:
                return found
            if depth >= limits["max_hops_from_search_seed"]:
                continue
            local = port.view(actor)
            for aid in local["known"]:
                if aid not in local["profiles"]:
                    request(actor, aid, "describe", depth)
            candidates = ranked(
                [p for p in port.view(actor)["profiles"].values() if p["agent_id"] not in visited],
                relay=True,
            )
            for profile in candidates:
                aid = profile["agent_id"]
                visited.add(aid)
                if request(actor, aid, "referral_forward", depth).get("delivered"):
                    brokers.append((aid, depth + 1))
                    break
        return central()
    result = referral("initiator", 0)
    if result is None:
        # Already explored recipients remain visited; fallback does not reset contact counters.
        result = central()
    return result


def port_for(runtime):
    def view(actor):
        state = runtime.read()
        return {**copy.deepcopy(state["views"][actor]), "clock": state["clock"]}

    return Discovery(
        view,
        lambda request: runtime.command("DISCOVER", request),
        runtime.config,
        runtime.episode["seed_bundle"]["tie_break"],
    )
