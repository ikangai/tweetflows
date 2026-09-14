"""Deterministic design expansion; this module does not execute any episode."""

import copy
import itertools
from importlib.resources import files

from tweetflows import __version__
from tweetflows.config import campaign_schema, digest, validate_campaign


def _planner_hash() -> str:
    package = files("tweetflows")
    return digest(
        {
            name: package.joinpath(name).read_text(encoding="utf-8")
            for name in ("__init__.py", "config.py", "planning.py")
        }
    )


def plan_campaign(value: object) -> dict:
    config = validate_campaign(value)
    infrastructure = copy.deepcopy(config)
    for key in ("campaign_id", "methods", "regimes", "replicate_seeds", "planning", "analysis"):
        infrastructure.pop(key)
    infrastructure["benchmark"].pop("task_ids")
    infrastructure["budget"].pop("campaign_limit")
    infrastructure_hash = digest(infrastructure)
    episodes = []
    dimensions = itertools.product(
        config["benchmark"]["task_ids"], config["regimes"], config["replicate_seeds"]
    )
    for task_id, regime, seed in dimensions:
        scenario = {
            "task_instance_id": task_id,
            "variant_id": "base",
            "regime": regime,
            "replicate_seed": seed,
            "infrastructure_hash": infrastructure_hash,
        }
        pair_id = "pair-" + digest(scenario)
        seed_bundle = {
            name: int(digest({"scenario": scenario, "stream": name})[:16], 16)
            for name in ("scenario", "topology", "availability", "duration", "tie_break", "model")
        }
        for method in config["methods"]:
            episodes.append(
                {
                    "schema_version": "1.0",
                    "episode_id": "ep-" + digest({"pair_id": pair_id, "method_id": method}),
                    "pair_id": pair_id,
                    "method_id": method,
                    "task_instance_id": task_id,
                    "template_id": task_id,
                    "variant_id": "base",
                    "regime_id": regime["id"],
                    "visibility": regime["visibility"],
                    "availability": regime["availability"],
                    "availability_trace": (
                        config["faults"]["availability_trace"]
                        if regime["availability"] == "churn"
                        else None
                    ),
                    "seed_bundle": seed_bundle.copy(),
                    "infrastructure_hash": infrastructure_hash,
                    "status": "PLANNED",
                }
            )
    upper_bound = len(episodes) * config["budget"]["per_episode_limit"]
    plan = {
        "schema_version": "1.0",
        "campaign_id": config["campaign_id"],
        "planner_version": __version__,
        "planner_source_hash": _planner_hash(),
        "schema_hash": digest(campaign_schema()),
        "configuration_hash": digest(config),
        "configuration": config,
        "execution_ready": False,
        "unresolved_execution_artifacts": [
            "fixture snapshots and tool implementations",
            "contact graph and historical evidence contents",
            "runtime, routing policies, worker and grader implementations",
        ],
        "episode_count": len(episodes),
        "pair_count": len({e["pair_id"] for e in episodes}),
        "budget": {
            "unit": config["budget"]["unit"],
            "campaign_limit": config["budget"]["campaign_limit"],
            "all_episodes_upper_bound": upper_bound,
            "all_episodes_guaranteed_fundable": upper_bound <= config["budget"]["campaign_limit"],
        },
        "episodes": episodes,
    }
    plan["plan_hash"] = digest(plan)
    return plan
