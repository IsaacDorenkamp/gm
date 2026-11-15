from dataclasses import dataclass


@dataclass
class Campaign:
    title: str


@dataclass
class Player:
    id: str
    name: str
    hp: int
