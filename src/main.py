from __future__ import annotations

import argparse

import initiative
import util


def initiative_tracker(_):
    entries = {}
    while True:
        try:
            charname = input("Character Name: ")
        except (EOFError, KeyboardInterrupt):
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
            break

        is_enemy = util.get_yesno("Is this character an enemy?", default=False)

        entries[charname] = (is_enemy, count)

    entries = [initiative.InitiativeEntry(charname, value, is_enemy) for charname, (is_enemy, value) in entries.items()]
    groups = initiative.sort(entries)
    for group in groups:
        is_enemy = group[0].is_enemy
        value = group[0].count
        characters = ', '.join(item.name for item in group)
        if is_enemy:
            print(f"\x1b[31;1m[{value}]\x1b[0m {characters}")
        else:
            print(f"\x1b[32;1m[{value}]\x1b[0m {characters}")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)
    initiative_tracker_parser = commands.add_parser("track")
    initiative_tracker_parser.set_defaults(func=initiative_tracker)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

