import models


def test_character_update_hp():
    c = models.Character(name="Test", max_hp=10, hp=10, temp_hp=0, is_enemy=False)
    c.update_hp(-15)
    assert c.hp == 0
    c.reset_hp()
    assert c.hp == 10
    assert c.temp_hp == 0
    c.set_hp(0)
    assert c.hp == 0
    c.update_hp(15)
    assert c.hp == 10
    assert c.temp_hp == 0
    c.set_hp(0)
    c.update_hp(15, overflow_temp=True)
    assert c.hp == 10
    assert c.temp_hp == 5
    c.reset_hp()
    c.temp_hp = 10
    c.update_hp(-15)
    assert c.hp == 5
    assert c.temp_hp == 0
    c.reset_hp()
    c.temp_hp = 10
    c.update_hp(-5)
    assert c.hp == 10
    assert c.temp_hp == 5

