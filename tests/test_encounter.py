import pytest

import encounter
import models


def make_character(name: str, is_enemy: bool = False) -> models.Character:
    return models.Character(name=name, max_hp=10, hp=10, temp_hp=0, is_enemy=is_enemy)


@pytest.fixture
def characters(request):
    return [make_character(name, is_enemy="Enemy" in name) for name in request.param]


def test_encounter_add_character():
    c = make_character("Test")
    e = encounter.Encounter()
    e.add_character(c, 10)

