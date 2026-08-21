from __future__ import annotations
from dataclasses import dataclass
from enum import auto, Enum, IntEnum, StrEnum
from typing import cast


class Ability(StrEnum):
    Str = "Strength"
    Dex = "Dexterity"
    Con = "Constitution"
    Int = "Intelligence"
    Wis = "Wisdom"
    Cha = "Charisma"


class Save(StrEnum):
    Fort = "Fortitude"
    Ref = "Reflex"
    Will = "Will"


@dataclass
class Abilities:
    Str: int
    Dex: int
    Con: int
    Int: int
    Wis: int
    Cha: int


@dataclass
class Saves:
    Fort: int
    Ref: int
    Will: int


class Skill(Enum):
    Acrobatics = auto()
    Arcana = auto()
    Athletics = auto()
    Crafting = auto()
    Deception = auto()
    Diplomacy = auto()
    Intimidation = auto()
    Lore = auto()
    Medicine = auto()
    Nature = auto()
    Occultism = auto()
    Performance = auto()
    Religion = auto()
    Society = auto()
    Stealth = auto()
    Survival = auto()
    Thievery = auto()


@dataclass
class Feature:
    name: str
    description: str


@dataclass
class Speeds:
    normal: int
    climb: int = 0
    swim: int = 0


class ActionCost(IntEnum):
    Free = 0
    One = 1
    Two = 2
    Three = 3
    Reaction = -1


class Die(IntEnum):
    d4 = 4
    d6 = 6
    d8 = 8
    d10 = 10
    d12 = 12
    d20 = 20
    d100 = 100


@dataclass
class DiceRoll:
    die: Die
    count: int
    mod: int = 0

    def __str__(self):
        result = f'{self.count}{self.die.name}'
        if self.mod == 0:
            return result
        else:
            sign = '+' if self.mod > 0 else '-'
            return f'{result} {sign} {abs(self.mod)}'


@dataclass
class SaveAction:
    save: Save
    dc: int


@dataclass
class StrikeAction:
    weapon: str
    modifier: int
    damage: DiceRoll


@dataclass
class CustomAction:
    description: str


@dataclass
class Action:
    cost: ActionCost
    action: StrikeAction | SaveAction | CustomAction
    name: str | None = None


@dataclass
class StatBlock:
    perception: int
    languages: list[str]
    skills: dict[Skill, int]
    abilities: Abilities
    ac: int
    saves: Saves
    weaknesses: dict[str, int]
    resistances: dict[str, int]
    immunities: list[str]
    features: list[Feature]
    speed: Speeds


@dataclass
class Character:
    name: str
    max_hp: int
    hp: int
    temp_hp: int
    is_enemy: bool

    def update_hp(self, diff: int, overflow_temp: bool = False):
        if diff < 0:
            if self.temp_hp > 0:
                portion = min(abs(diff), self.temp_hp)
                diff += portion  # add, because diff is negative
                self.temp_hp -= portion
            self.hp = max(0, self.hp + diff)
        else:
            to_add = min(self.max_hp - self.hp, diff)
            diff -= to_add
            self.hp += to_add
            if overflow_temp:
                self.temp_hp += diff

    def set_hp(self, hp: int):
        self.hp = min(self.max_hp, max(0, hp))

    def reset_hp(self):
        self.hp = self.max_hp
        self.temp_hp = 0


@dataclass
class NPC(Character):
    statblock: StatBlock


@dataclass
class EncounterDefinition:
    name: str
    monsters: list[NPC]
    allies: list[NPC]


@dataclass
class InitiativeKey:
    count: int
    is_enemy: bool

    def __hash__(self):
        return hash((self.count, self.is_enemy))

    def __lt__(self, other: InitiativeKey) -> bool:
        # higher counts should come first
        if self.count == other.count:
            return self.is_enemy > other.is_enemy
        else:
            return self.count > other.count

    def __eq__(self, other_obj: object) -> bool:
        if isinstance(other_obj, InitiativeKey):
            other = cast(InitiativeKey, other_obj)
            return self.count == other.count and self.is_enemy == other.is_enemy
        else:
            return False


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


@dataclass
class InitiativeCount(InitiativeKey):
    characters: list[str]


@dataclass
class Player:
    id: str
    name: str
    max_hp: int

