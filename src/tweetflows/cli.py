"""Command-line validation, planning, and opt-in controlled agent execution."""

import argparse
import json
import sys
from pathlib import Path

from tweetflows import __version__
from tweetflows.config import ConfigurationError, digest, load_campaign
from tweetflows.execution import run_campaign
from tweetflows.live import ChatWorker
from tweetflows.planning import plan_campaign
from tweetflows.store import ExecutionError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentflow", description=__doc__)
    parser.add_argument("--version", action="version", version=f"tweetflows {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Check a fixture campaign configuration")
    validate.add_argument("campaign", type=Path)
    plan = commands.add_parser("plan", help="Generate a reproducible plan without executing it")
    plan.add_argument("campaign", type=Path)
    plan.add_argument(
        "--output", type=Path, help="Create a new plan file; default: standard output"
    )
    run = commands.add_parser("run", help="Execute controlled fixture tasks")
    run.add_argument("campaign", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    run.add_argument(
        "--provider", type=Path, help="Live worker settings; credentials stay in the environment"
    )
    run.add_argument("--resume", action="store_true", help="Continue the same output directory")
    args = parser.parse_args(argv)
    try:
        config = load_campaign(args.campaign)
        if args.command == "validate":
            result = {
                "valid": True,
                "campaign_id": config["campaign_id"],
                "configuration_hash": digest(config),
                "scope": "fixture planning only",
            }
        elif args.command == "run":
            if (args.mode == "live") != (args.provider is not None):
                raise ExecutionError("Live mode requires --provider; fixture mode forbids it")
            worker = ChatWorker(json.loads(args.provider.read_text())) if args.provider else None
            result = run_campaign(config, args.output, resume=args.resume, worker=worker)
        else:
            result = plan_campaign(config)
        rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.command == "plan" and args.output is not None:
            # Exclusive creation preserves existing plans and the source configuration.
            with args.output.open("x", encoding="utf-8") as target:
                target.write(rendered)
            print(f"Planned {result['episode_count']} episodes in {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(rendered)
    except (ConfigurationError, ExecutionError, OSError, json.JSONDecodeError) as exc:
        print(f"agentflow: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
