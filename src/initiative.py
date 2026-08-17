from __future__ import annotations

from dataclasses import dataclass

import util






def sort(entries: list[InitiativeEntry]) -> list[list[InitiativeEntry]]:
    sorted_entries = sorted(entries, reverse=True)
    return util.aggregate(sorted_entries, key=lambda entry: (entry.count, entry.is_enemy))


__all__ = ["InitiativeEntry", "sort"]
