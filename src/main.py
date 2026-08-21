from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import traceback

import encounter
import initiative
import models
import repo
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


def initialize(_) -> int:
    gm_dir = os.environ.get("GM_DIR")
    if gm_dir:
        at = pathlib.Path(gm_dir)
        if not at.exists():
            at.mkdir(parents=True)
    else:
        at = pathlib.Path(os.getcwd())

    # TODO: check if a complete initialization has already occurred

    with open(at / "players.json", "w") as fp:
        json.dump({}, fp)

    print(f"\x1b[32;1mSuccessfully\x1b[0m initialized campaign at {at}")
    return 0


def add_player(args):
    player = models.Player(id=args.id, name=args.name, max_hp=args.hp)
    try:
        repo.players.create(player)
        repo.players.sync()
    except repo.RepoError as err:
        print(f"\x1b[31;1mError:\x1b[0m {err}")
        return 1
    print(f"\x1b[32;1mSuccessfully\x1b[0m Created player \x1b[1m{player.id}\x1b[0m")


def list_players(_):
    try:
        for player in repo.players.all():
            print(f"\x1b[1m{player.id}\x1b[0m: {player.name} (\x1b[32m{player.max_hp}hp\x1b[0m)")
    except repo.RepoError as err:
        print(f"\x1b[31;1mError:\x1b[0m {err}")


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)

    initialize_parser = commands.add_parser("init")
    initialize_parser.set_defaults(func=initialize)

    initiative_tracker_parser = commands.add_parser("track")
    initiative_tracker_parser.set_defaults(func=initiative_tracker)

    player_parser = commands.add_parser("players")
    player_commands = player_parser.add_subparsers(required=True)

    add_player_cmd = player_commands.add_parser("add")
    add_player_cmd.add_argument("--id", type=str, help="Player ID, used to succinctly identify the player.", required=True)
    add_player_cmd.add_argument("--name", type=str, help="Display name for the player.", required=True)
    add_player_cmd.add_argument("--hp", type=int, help="Player's max HP.", required=True)
    add_player_cmd.set_defaults(func=add_player)

    list_players_cmd = player_commands.add_parser("list")
    list_players_cmd.set_defaults(func=list_players)

    encounter_parser = commands.add_parser("encounter")
    encounter_commands = encounter_parser.add_subparsers(required=True)

    run_encounter_parser = encounter_commands.add_parser("run")
    run_encounter_parser.set_defaults(func=encounter.run_encounter)

    args = parser.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())

