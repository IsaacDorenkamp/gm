import dataclasses
import functools
import json
import os
import pathlib
from typing import Self

from models import Player


GM_DIR = os.environ.get("GM_DIR")


class RepoError(Exception):
    """
    An error to be raised when an operation in repository logic fails.
    """


class PlayerRepo:
    __root: pathlib.Path
    __loaded: bool
    __players: dict[str, Player]

    def __init__(self, root: pathlib.Path):
        self.__root = root
        self.__loaded = False
        self.__players = {}

    @staticmethod
    def check(fn):
        @functools.wraps(fn)
        def newfn(self: Self, *args, **kwargs):
            if not self.__loaded:
                self.__load()
            return fn(self, *args, **kwargs)
        return newfn

    def __load(self):
        try:
            with open(self.__root / "players.json") as fp:
                data = json.load(fp)
            self.__players = { key: Player(**value) for key, value in data.items() }
        except IOError as ioe:
            raise RepoError("Unable to read players.json") from ioe
        except json.JSONDecodeError as jde:
            raise RepoError("players.json contains invalid JSON") from jde

    @check
    def get(self, player_id: str) -> Player:
        try:
            return self.__players[player_id]
        except KeyError as ke:
            raise RepoError(f"No player with ID '{player_id}'") from ke

    @check
    def create(self, player: Player):
        if player.id in self.__players:
            raise RepoError(f"A player with ID '{player.id}' already exists!")
        self.__players[player.id] = player

    @check
    def all(self) -> list[Player]:
        return sorted(self.__players.values(), key=lambda x: x.id)

    def sync(self):
        data = { key: dataclasses.asdict(player) for key, player in self.__players.items() }
        with open(self.__root / "players.json", "w") as fp:
            json.dump(data, fp)


players = PlayerRepo(pathlib.Path(GM_DIR or os.getcwd()))


__all__ = ["players", "PlayerRepo"]

