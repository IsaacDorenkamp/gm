from initiative import *


def test_initiative_ordered_correctly_general_case():
    """Ensure that, in the general case with no overlapping counts,
    the initiative sorter orders entities correctly.
    """
    result = sort([
        InitiativeEntry(name="Party Member 1", count=14, is_enemy=False),
        InitiativeEntry(name="Party Member 2", count=4, is_enemy=False),
        InitiativeEntry(name="Party Member 3", count=17, is_enemy=False),
        InitiativeEntry(name="Party Member 4", count=8, is_enemy=False),
        InitiativeEntry(name="Monster 1", count=15, is_enemy=True),
        InitiativeEntry(name="Monster 2", count=18, is_enemy=True),
        InitiativeEntry(name="Monster 3", count=20, is_enemy=True),
    ])

    assert len(result) == 7
    assert all([len(group) == 1 for group in result])
    names = [group[0].name for group in result]
    assert names[0] == "Monster 3"
    assert names[1] == "Monster 2"
    assert names[2] == "Party Member 3"
    assert names[3] == "Monster 1"
    assert names[4] == "Party Member 1"
    assert names[5] == "Party Member 4"
    assert names[6] == "Party Member 2"


def test_initiative_ordered_correctly_shared_count():
    """Ensure that, in the case that two entities on the same
    side share an initiative count, that they are grouped together.
    """
    result = sort([
        InitiativeEntry(name="Party Member 1", count=10, is_enemy=False),
        InitiativeEntry(name="Party Member 2", count=10, is_enemy=False),
        InitiativeEntry(name="Monster 1", count=5, is_enemy=True),
        InitiativeEntry(name="Monster 2", count=5, is_enemy=True),
    ])
    assert len(result) == 2
    assert all([len(group) == 2 for group in result])
    assert result[0][0].name == "Party Member 1"
    assert result[0][1].name == "Party Member 2"
    assert result[1][0].name == "Monster 1"
    assert result[1][1].name == "Monster 2"


def test_initiative_ordered_correctly_shared_count_enemies():
    """Ensure that, when allies and enemies share an initiative count,
    that they are grouped separately, and that the enemies go first.
    """
    result = sort([
        InitiativeEntry(name="Party Member 1", count=10, is_enemy=False),
        InitiativeEntry(name="Party Member 2", count=10, is_enemy=False),
        InitiativeEntry(name="Monster 1", count=10, is_enemy=True),
        InitiativeEntry(name="Monster 2", count=10, is_enemy=True),
    ])
    assert len(result) == 2
    assert all([len(group) == 2 for group in result])
    assert result[0][0].name == "Monster 1"
    assert result[0][1].name == "Monster 2"
    assert result[1][0].name == "Party Member 1"
    assert result[1][1].name == "Party Member 2"

