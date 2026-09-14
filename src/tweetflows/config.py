"""Strict fixture configuration contracts, with no network schema resolution."""

import copy
import hashlib
import json
import math
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator


class ConfigurationError(ValueError):
    """The campaign cannot be planned under the supported contract."""


def canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ConfigurationError(f"Non-finite JSON number: {value}")


def load_campaign(path: Path) -> dict:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ConfigurationError(f"Invalid UTF-8 JSON: {exc}") from exc
    return validate_campaign(value)


def campaign_schema() -> dict:
    resource = files("tweetflows").joinpath("schemas", "campaign.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_campaign(value: object) -> dict:
    try:
        canonical_json(value)
    except (ValueError, TypeError) as exc:
        raise ConfigurationError("Campaign must contain only finite JSON values") from exc
    validator = Draft202012Validator(campaign_schema())
    errors = sorted(validator.iter_errors(value), key=lambda e: str(list(e.absolute_path)))
    if errors:
        details = []
        for error in errors[:10]:
            location = ".".join(map(str, error.absolute_path)) or "$"
            details.append(f"{location}: {error.message}")
        raise ConfigurationError("\n".join(details))

    config = copy.deepcopy(value)
    benchmark = config["benchmark"]
    visibility = config["visibility"]
    regimes = config["regimes"]
    if len({r["id"] for r in regimes}) != len(regimes):
        raise ConfigurationError("regimes: IDs must be unique")
    if visibility["initial_profile_count_full"] != benchmark["agent_count"]:
        raise ConfigurationError("visibility: full view must contain all agents")
    if visibility["initial_profile_count_partial"] >= benchmark["agent_count"]:
        raise ConfigurationError(
            "visibility: partial view must contain fewer agents than full view"
        )
    discovery = config["discovery"]
    if discovery["max_contacts_per_search"] > discovery["max_contacts_per_root"]:
        raise ConfigurationError("discovery: search contact limit exceeds root limit")
    for name in ("candidate_weights", "relay_weights"):
        if not math.isclose(sum(discovery[name].values()), 1.0, rel_tol=0, abs_tol=1e-9):
            raise ConfigurationError(f"discovery.{name}: weights must sum to 1")
    if config["execution"]["max_child_depth"] >= config["execution"]["max_tasks_per_root"]:
        raise ConfigurationError("execution: child depth cannot fit within the root task count")
    pairs = len(benchmark["task_ids"]) * len(regimes) * len(config["replicate_seeds"])
    episodes = pairs * len(config["methods"])
    if config["planning"]["expected_pairs"] != pairs:
        raise ConfigurationError(f"planning.expected_pairs: expected {pairs}")
    if config["planning"]["expected_episodes"] != episodes:
        raise ConfigurationError(f"planning.expected_episodes: expected {episodes}")
    if config["budget"]["campaign_limit"] < config["budget"]["per_episode_limit"]:
        raise ConfigurationError("budget: campaign cannot reserve even one episode")
    if not set(config["analysis"]["primary_pair"]) <= set(config["methods"]):
        raise ConfigurationError("analysis.primary_pair: both methods must be in the campaign")

    # These lists are sets of experiment dimensions; their order is not scientific input.
    config["methods"].sort()
    config["replicate_seeds"].sort()
    benchmark["task_ids"].sort()
    config["regimes"].sort(key=lambda regime: regime["id"])
    return config
