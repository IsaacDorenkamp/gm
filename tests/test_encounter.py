import pytest

import encounter
import models


def make_character(name: str, is_enemy: bool = False) -> models.Character:
    return models.Character(name=name, max_hp=10, hp=10, temp_hp=0, is_enemy=is_enemy)


def group_names(groups: list[encounter.InitiativeGroup]):
    return [[entry for entry in group.characters] for group in groups]


@pytest.fixture
def characters(request):
    return [make_character(name, is_enemy="Enemy" in name) for name in request.param]


def test_encounter_add_character():
    c = make_character("Test")
    e = encounter.Encounter()
    e.add_character(c, 10)
    assert group_names(e.initiative_groups) == [["Test"]]


with_characters = pytest.mark.parametrize("characters", (("Enemy 1", "Enemy 2", "Player 1", "Player 2"),), indirect=True)


@with_characters
def test_encounter_add_character_multiple(characters: list[models.Character]):
    e1, e2, p1, p2 = characters
    e = encounter.Encounter()
    e.add_character(e1, 10)
    e.add_character(e2, 10)
    e.add_character(p1, 10)
    e.add_character(p2, 5)
    assert group_names(e.initiative_groups) == [["Enemy 1", "Enemy 2"], ["Player 1"], ["Player 2"]]


@with_characters
def test_encounter_add_character_during_encounter(characters: list[models.Character]):
    e1, e2, p1, p2 = characters
    e = encounter.Encounter()
    e.add_character(e1, 10)
    e.add_character(p1, 9)
    e.add_character(p2, 9)
    assert group_names(e.initiative_groups) == [["Enemy 1"], ["Player 1", "Player 2"]]
    e.begin()
    assert e.active_character.name == "Enemy 1"
    e.next_turn()
    assert e.active_character.name == "Player 1"
    e.add_character(e2, 15)
    assert e.active_character.name == "Player 1"
    assert group_names(e.initiative_groups) == [["Enemy 2"], ["Enemy 1"], ["Player 1", "Player 2"]]


@with_characters
def test_encounter_remove_character(characters: list[models.Character]):
    e1, e2, p1, p2 = characters
    e = encounter.Encounter()
    e.add_character(e1, 10)
    e.add_character(e2, 10)
    e.add_character(p1, 10)
    e.add_character(p2, 10)
    e.remove_character("Player 1")
    assert group_names(e.initiative_groups) == [["Enemy 1", "Enemy 2"], ["Player 2"]]


@with_characters
def test_encounter_remove_character_during_encounter(characters: list[models.Character]):
    e1, e2, p1, p2 = characters
    e = encounter.Encounter()
    e.add_character(e1, 10)
    e.add_character(e2, 10)
    e.add_character(p1, 10)
    e.add_character(p2, 10)
    e.begin()
    e.next_turn()
    assert e.active_character.name == "Enemy 2"
    e.remove_character("Enemy 1")
    assert e.active_character.name == "Enemy 2"


@with_characters
def test_encounter_cycle_through_order(characters: list[models.Character]):
    e = encounter.Encounter()
    for index, character in enumerate(characters):
        e.add_character(character, 20 - index)

    e.begin()
    for i in range(len(characters)):
        assert e.active_character.name == characters[i].name
        e.next_turn()

    assert e.active_character.name == characters[0].name


def test_encounter_prevent_duplicate_name():
    e = encounter.Encounter()
    e.add_character(make_character("Test"), 10)
    with pytest.raises(ValueError, match="A character named 'Test' already exists!"):
        e.add_character(make_character("Test"), 10)


def test_begin_twice_fails():
    e = encounter.Encounter()
    e.add_character(make_character("Test"), 10)
    e.begin()
    with pytest.raises(ValueError, match="Already started!"):
        e.begin()


def test_no_active_character_before_begin():
    e = encounter.Encounter()
    with pytest.raises(ValueError, match="Encounter is not active!"):
        e.active_character


def test_begin_fails_with_no_characters():
    e = encounter.Encounter()
    with pytest.raises(ValueError, match="No characters are in initiative!"):
        e.begin()


@with_characters
def test_remove_character_after_begin_resets(characters: list[models.Character]):
    e = encounter.Encounter()
    for c in characters:
        e.add_character(c, 10)
    e.begin()
    assert e.active_character.name == characters[0].name
    for c in characters:
        e.remove_character(c.name)
    assert e.actions == 0
    with pytest.raises(ValueError, match="Encounter is not active!"):
        e.active_character

