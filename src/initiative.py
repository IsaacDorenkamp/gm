from __future__ import annotations

from dataclasses import dataclass

import util


@dataclass
class InitiativeEntry:
    name: str
    count: int
    is_enemy: bool

    def __lt__(self, other: InitiativeEntry) -> bool:
        if self.count == other.count:
            return self.is_enemy < other.is_enemy
        else:
            return self.count < other.count



def sort(entries: list[InitiativeEntry]) -> list[list[InitiativeEntry]]:
    sorted_entries = sorted(entries, reverse=True)
    return util.aggregate(sorted_entries, key=lambda entry: (entry.count, entry.is_enemy))


__all__ = ["InitiativeEntry", "sort"]
