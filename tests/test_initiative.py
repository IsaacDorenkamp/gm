from initiative import Roster
from models import Character


def make_character(name: str, is_enemy: bool = False):
    return Character(name=name, max_hp=10, hp=10, temp_hp=0, is_enemy=is_enemy)


def test_initiative_ordered_correctly_general_case():
    """Ensure that, in the general case with no overlapping counts,
    the initiative sorter orders entities correctly.
    """
    roster = Roster()
    roster.add_character("Party Member 1", False, 14)
    roster.add_character("Party Member 2", False, 4)
    roster.add_character("Party Member 3", False, 17)
    roster.add_character("Party Member 4", False, 8)
    roster.add_character("Monster 1", True, 15)
    roster.add_character("Monster 2", True, 18)
    roster.add_character("Monster 3", True, 20)
    assert roster.characters == [
        "Monster 3", "Monster 2", "Party Member 3", "Monster 1",
        "Party Member 1", "Party Member 4", "Party Member 2",
    ]


def test_initiative_ordered_correctly_shared_count():
    """Ensure that, in the case that two entities on the same
    side share an initiative count, that they are grouped together.
    """
    roster = Roster()
    roster.add_character("Party Member 1", False, 10)
    roster.add_character("Party Member 2", False, 10)
    roster.add_character("Monster 1", True, 5)
    roster.add_character("Monster 2", True, 5)
    
    counts = roster.counts
    assert len(counts) == 2
    assert counts[0].characters == ["Party Member 1", "Party Member 2"]
    assert counts[1].characters == ["Monster 1", "Monster 2"]


def test_initiative_ordered_correctly_shared_count_enemies():
    """Ensure that, when allies and enemies share an initiative count,
    that they are grouped separately, and that the enemies go first.
    """
    roster = Roster()
    roster.add_character("Party Member 1", False, 10)
    roster.add_character("Party Member 2", False, 10)
    roster.add_character("Monster 1", True, 10)
    roster.add_character("Monster 2", True, 10)
    
    counts = roster.counts
    assert len(counts) == 2
    assert counts[0].characters == ["Monster 1", "Monster 2"]
    assert counts[1].characters == ["Party Member 1", "Party Member 2"]

