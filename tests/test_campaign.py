import copy
import json
import socket
from collections import defaultdict
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tweetflows.cli import main
from tweetflows.config import (
    ConfigurationError,
    campaign_schema,
    digest,
    load_campaign,
    validate_campaign,
)
from tweetflows.planning import plan_campaign

EXAMPLE = Path(__file__).parents[1] / "configs" / "fixture-smoke.json"


@pytest.fixture
def campaign():
    return json.loads(EXAMPLE.read_text())


def test_schema_is_valid():
    Draft202012Validator.check_schema(campaign_schema())


def test_reference_plan_has_72_episodes_in_complete_groups(campaign):
    """T21: cardinality and comparable infrastructure, not just an output snapshot."""
    plan = plan_campaign(campaign)
    assert plan["episode_count"] == 72
    assert len({e["episode_id"] for e in plan["episodes"]}) == 72
    groups = defaultdict(list)
    for episode in plan["episodes"]:
        groups[episode["pair_id"]].append(episode)
    assert len(groups) == plan["pair_count"] == 24
    for group in groups.values():
        assert {e["method_id"] for e in group} == set(campaign["methods"])
        assert len({digest(e["seed_bundle"]) for e in group}) == 1
        assert len({e["infrastructure_hash"] for e in group}) == 1
    assert plan["budget"]["all_episodes_upper_bound"] == 864000
    assert plan["budget"]["all_episodes_guaranteed_fundable"]
    assert not plan["execution_ready"]


def test_stable_regimes_never_receive_churn_trace(campaign):
    episodes = plan_campaign(campaign)["episodes"]
    for episode in episodes:
        if episode["availability"] == "stable":
            assert episode["availability_trace"] is None
        else:
            assert episode["availability_trace"] == "fixture_churn_v1"


def test_dimension_reordering_preserves_entire_plan_and_input(campaign):
    before = copy.deepcopy(campaign)
    expected = plan_campaign(campaign)
    assert campaign == before
    for key in ("methods", "regimes", "replicate_seeds"):
        campaign[key].reverse()
    campaign["benchmark"]["task_ids"].reverse()
    assert plan_campaign(campaign) == expected


def test_method_subset_keeps_existing_pair_and_episode_ids(campaign):
    expected = plan_campaign(campaign)
    campaign["methods"].remove("intent_local_v1")
    campaign["planning"]["expected_episodes"] = 48
    subset = plan_campaign(campaign)
    assert subset["episodes"] == [
        e for e in expected["episodes"] if e["method_id"] != "intent_local_v1"
    ]


def test_budget_change_separates_incompatible_pairs(campaign):
    before = plan_campaign(campaign)
    campaign["budget"]["per_episode_limit"] += 1
    after = plan_campaign(campaign)
    assert {e["pair_id"] for e in before["episodes"]}.isdisjoint(
        e["pair_id"] for e in after["episodes"]
    )
    assert not after["budget"]["all_episodes_guaranteed_fundable"]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("mode",), "live"),
        (("model", "network_enabled"), True),
        (("model", "adapter"), "unknown"),
        (("model", "extra_field"), "ignored?"),
        (("benchmark", "task_ids"), ["direct_update", "direct_update"]),
        (("replicate_seeds",), [11, 11, 33]),
        (("budget", "per_episode_limit"), -1),
        (("budget", "campaign_limit"), 1),
        (("discovery", "candidate_weights", "match"), 0.8),
        (("discovery", "max_contacts_per_root"), 1),
        (("planning", "expected_episodes"), 73),
        (("planning", "expected_pairs"), 25),
        (("regimes", 1, "id"), "full_stable"),
        (("visibility", "initial_profile_count_full"), 7),
        (("visibility", "initial_profile_count_partial"), 8),
        (("verification", "grader_visible_during_episode"), True),
        (("execution", "max_child_depth"), 4),
        (("time_model", "duration_ticks", "wait"), 0),
        (("time_model", "same_time_order"), ["completion", "expiry", "availability", "decision"]),
        (("reputation", "update_during_episode"), True),
        (("analysis", "confidence_level"), float("inf")),
    ],
)
def test_invalid_campaign_rejected(campaign, path, value):
    target = campaign
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ConfigurationError):
        validate_campaign(campaign)


@pytest.mark.parametrize("text", ['{"mode":"fixture","mode":"live"}', '{"x":NaN}', "{"])
def test_ambiguous_or_malformed_json_rejected(tmp_path, text):
    path = tmp_path / "campaign.json"
    path.write_text(text)
    with pytest.raises(ConfigurationError):
        load_campaign(path)


def test_cli_plan_needs_no_network_and_refuses_overwrite(tmp_path, monkeypatch, capsys):
    def unexpected_network(*args, **kwargs):
        pytest.fail("Planning attempted network access")

    monkeypatch.setattr(socket, "socket", unexpected_network)
    output = tmp_path / "plan.json"
    args = ["plan", str(EXAMPLE), "--output", str(output)]
    assert main(args) == 0
    original = output.read_bytes()
    assert json.loads(original)["episode_count"] == 72
    assert main(args) == 2
    assert output.read_bytes() == original
    assert "Traceback" not in capsys.readouterr().err


def test_cli_validation_and_errors(capsys, tmp_path):
    assert main(["validate", str(EXAMPLE)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"]
    assert main(["validate", str(tmp_path / "missing.json")]) == 2
    assert "Traceback" not in capsys.readouterr().err


def test_plan_hash_covers_all_other_fields(campaign):
    plan = plan_campaign(campaign)
    recorded = plan.pop("plan_hash")
    assert recorded == digest(plan)
