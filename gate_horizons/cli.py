"""Command-line utilities for Gate Horizons."""

from __future__ import annotations

import argparse
from pathlib import Path

from gate_horizons.game.state import GameState


def _load_state(save_path: str | None) -> GameState:
    if save_path and Path(save_path).exists():
        return GameState().load(save_path)
    return GameState.new_game()


def _save_state(state: GameState, save_path: str | None) -> None:
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        state.save(save_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate Horizons utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export-encounter", help="Generate EncounterSpec.json"
    )
    export_parser.add_argument("--system", required=True, help="System id")
    export_parser.add_argument("--type", default="pirates", help="Encounter type")
    export_parser.add_argument(
        "--exports-dir",
        default="exports/encounters",
        help="Folder to write EncounterSpec.json",
    )
    export_parser.add_argument(
        "--save",
        help="Optional save file path to load/persist pending encounters",
    )

    import_parser = subparsers.add_parser(
        "import-result", help="Import ResultSpec.json and apply consequences"
    )
    import_parser.add_argument(
        "--imports-dir",
        default="imports/results",
        help="Folder containing ResultSpec.json",
    )
    import_parser.add_argument(
        "--save",
        required=True,
        help="Save file path to load and update",
    )

    args = parser.parse_args()

    if args.command == "export-encounter":
        state = _load_state(args.save)
        success, message = state.export_encounter_spec(
            system_id=args.system,
            encounter_type=args.type,
            exports_dir=args.exports_dir,
        )
        if success:
            _save_state(state, args.save)
        print(message)
        return

    if args.command == "import-result":
        state = _load_state(args.save)
        success, message = state.import_result_spec(
            imports_dir=args.imports_dir,
        )
        if success:
            _save_state(state, args.save)
        print(message)
        return


if __name__ == "__main__":
    main()
