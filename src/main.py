from __future__ import annotations

import argparse
import os
import pathlib

import encounter
import initiative
import models
import util


def initiative_tracker(_):
    print("When done entering characters, press Ctrl+D or Ctrl+C, or enter an empty name.")
    entries = {}
    while True:
        try:
            charname = input("Character Name: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not charname:
            break

        if charname in entries:
            print("A character with that name already exists. Enter a different one.")
            continue

        count = None
        while count is None:
            try:
                raw_count = input("Initiative Position: ")
                count = int(raw_count)
            except (EOFError, KeyboardInterrupt):
                break
            except ValueError:
                print("Please enter an integer value.")

        if count is None:
            print()
            break

        is_enemy = util.get_yesno("Is this character an enemy?", default=False)

        entries[charname] = (is_enemy, count)

    roster = initiative.Roster()
    for name, (is_enemy, count) in entries.items():
        c = models.Character(name=name, max_hp=1, hp=1, temp_hp=0, is_enemy=is_enemy)
        roster.add_character(c, count)
    for group in roster.counts:
        characters = ', '.join(item for item in group.characters)
        if group.is_enemy:
            print(f"\x1b[31;1m[{group.count}]\x1b[0m {characters}")
        else:
            print(f"\x1b[32;1m[{group.count}]\x1b[0m {characters}")


def initialize(_):
    c = models.Campaign()
    at = pathlib.Path(os.getcwd())
    try:
        c.save(pathlib.Path(at), exist_ok=False)
    except Exception as exc:
        print(f"\x1b[31;1mError:\x1b[0m {str(exc)}")
        return 1

    print(f"\x1b[32;1mSuccessfully\x1b[0m initialized campaign at {at}")


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)

    initialize_parser = commands.add_parser("init")
    initialize_parser.set_defaults(func=initialize)

    initiative_tracker_parser = commands.add_parser("track")
    initiative_tracker_parser.set_defaults(func=initiative_tracker)

    encounter_parser = commands.add_parser("encounter")
    encounter_commands = encounter_parser.add_subparsers(required=True)

    run_encounter_parser = encounter_commands.add_parser("run")
    run_encounter_parser.set_defaults(func=encounter.run_encounter)

    args = parser.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

