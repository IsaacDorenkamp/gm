from __future__ import annotations

import bisect

from models import Character, InitiativeCount, InitiativeKey


class Roster:
    __counts: list[InitiativeCount]
    __characters: dict[str, InitiativeKey]

    def __init__(self):
        self.__counts = []
        self.__characters = {}

    def add_character(self, character: Character, count: int):
        if character.name in self.__characters:
            raise ValueError(f"Character '{character.name}' is already in turn order!")
        key = InitiativeKey(count=count, is_enemy=character.is_enemy)
        self.__characters[character.name] = key
        exist_count = next((count for count in self.__counts if key == count), None)
        if exist_count:
            exist_count.characters.append(character.name)
        else:
            new_count = InitiativeCount(count=count, is_enemy=character.is_enemy, characters=[character.name])
            bisect.insort(self.__counts, new_count)

    def remove_character(self, character: Character | str):
        if isinstance(character, Character):
            character = character.name
        key = self.__characters.get(character)
        if key is None:
            raise ValueError(f"No character exists in initiative: {character}")
        else:
            idx, count = next((entry for entry in enumerate(self.__counts) if key == entry[1]))
            count.characters.remove(character)
            del self.__characters[character]
            if not count.characters:
                self.__counts.pop(idx)

    @property
    def counts(self) -> list[InitiativeCount]:
        return self.__counts

    @property
    def characters(self) -> list[str]:
        characters = []
        for count in self.__counts:
            characters.extend(count.characters)
        return characters


__all__ = ["Roster"]
