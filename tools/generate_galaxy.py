"""Generate a galaxy JSON from a seed, optionally pinning known systems."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gate_horizons.game.galaxy import GalaxyMap


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a galaxy JSON file.")
    parser.add_argument("--seed", type=int, default=0, help="Seed for deterministic generation")
    parser.add_argument("--system-count", type=int, default=12, help="Number of systems")
    parser.add_argument("--known", nargs="*", default=[], help="Known system IDs to pin")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path")

    args = parser.parse_args()

    galaxy = GalaxyMap()
    galaxy.generate_procedural(
        seed=args.seed,
        system_count=args.system_count,
        known_system_ids=set(args.known or []),
    )

    payload = galaxy.to_dict()
    payload["seed"] = args.seed
    payload["system_count"] = args.system_count
    payload["known_systems"] = list(args.known or [])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
