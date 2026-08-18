import bisect
from collections import defaultdict
import curses
import curses.textpad
from dataclasses import dataclass
from typing import Generator

import gcurses
from models import Action, Character, InitiativeCount, InitiativeKey
import util


@dataclass
class InitiativeGroup:
    characters: list[str]
    count: int


class Encounter:
    __initiative: list[tuple[InitiativeKey, Character]]
    __active: int

    # log
    __action_log: list[tuple[str, Action]]

    # current turn state
    __actions: int

    def __init__(self):
        self.__initiative = []
        self.__active = -1
        self.__actions = 0

    def add_character(self, character: Character, initiative: int):
        if self.__has_character(character.name):
            raise ValueError("A character named '%s' already exists!" % character.name)
        key = InitiativeKey(count=initiative, is_enemy=character.is_enemy)
        index = bisect.bisect(self.__initiative, key, key=lambda x: x[0])
        if index <= self.__active:
            self.__active += 1
        self.__initiative.insert(index, (key, character))

    def remove_character(self, name: str):
        index = [entry[1].name for entry in self.__initiative].index(name)
        if index <= self.__active:
            self.__active -= 1
        self.__initiative.pop(index)
        if not self.__initiative:
            self.__active = -1
            self.__actions = 0

    def begin(self):
        if self.__active == -1:
            if self.__initiative:
                self.__active = 0
                self.__actions = 3
            else:
                raise ValueError("No characters are in initiative!")
        else:
            raise ValueError("Already started!")

    def act(self, action: Action) -> bool:
        if self.__actions >= action.cost:
            self.__actions -= action.cost
            # TODO: copy action instance?
            self.__action_log.append((self.active_character.name, action))
            return True
        else:
            return False

    def next_turn(self):
        self.__active = (self.__active + 1) % len(self.__initiative)
        self.__actions = 3

    def update_character_hp(self, name: str, diff: int):
        char = self.__find_character(name)
        char.update_hp(diff)

    def set_character_hp(self, name: str, hp: int):
        char = self.__find_character(name)
        char.set_hp(hp)

    def __has_character(self, name: str) -> bool:
        return any((entry[1].name == name for entry in self.__initiative))

    def __find_character(self, name: str) -> Character:
        try:
            return next((entry[1] for entry in self.__initiative if entry[1].name == name))
        except StopIteration:
            raise ValueError("Could not find character by name '%s'" % name)

    @property
    def active_character(self) -> Character:
        if self.__active >= 0:
            return self.__initiative[self.__active][1]
        else:
            raise ValueError("Encounter is not active!")

    @property
    def initiative_groups(self) -> list[InitiativeGroup]:
        agg = util.aggregate(self.__initiative, key=lambda x: x[0])
        return [InitiativeGroup(characters=[entry[1].name for entry in group], count=group[0][0].count) for group in agg]

    @property
    def actions(self) -> int:
        return self.__actions

    @property
    def characters(self) -> Generator[Character, None, None]:
        for x in self.__initiative:
            yield x[1]


class InitiativeWindow:
    ALLY_COLOR  = curses.COLOR_GREEN
    ENEMY_COLOR = curses.COLOR_RED

    __pos: tuple[int, int]
    __size: tuple[int, int]
    __box: gcurses.WrapBox
    __pad: curses.window

    __name_blocks: dict[str, list[curses.window]]
    __counts: dict[int, int]

    __selected: str | None

    def __init__(self, entries: list[InitiativeCount], size: tuple[int, int], pos: tuple[int, int] = (0, 0)):
        self.__pos = pos
        self.__size = size
        self.__box = gcurses.WrapBox(size[1] - 3)
        self.__counts = {}
        self.__name_blocks = {}
        self.__selected = None
        self.__generate(entries)

    def __generate(self, entries: list[InitiativeCount]):
        ally_pair = gcurses.pair(self.ALLY_COLOR, -1)
        enemy_pair = gcurses.pair(self.ENEMY_COLOR, -1)

        self.__counts.clear()
        self.__name_blocks.clear()
        blocks = defaultdict(list)
        countblocks = defaultdict(list)
        self.__box.clear()
        for entry in entries:
            self.__counts[entry.count] = self.__box.line
            countblocks[enemy_pair if entry.is_enemy else ally_pair].extend(self.__box.write("[%02d] " % entry.count))
            self.__box.indent = 5
            for idx, name in enumerate(entry.characters):
                if idx > 0:
                    self.__box.write(', ')
                for block in self.__box.write(name):
                    blocks[name].append(block)
            self.__box.indent = 0
            self.__box.linebreak()

        self.__pad = curses.newpad(self.__box.nlines, self.__box.width)
        for name, text_blocks in blocks.items():
            self.__name_blocks[name] = [self.__pad.subpad(1, block[2], block[0], block[1]) for block in text_blocks]

        width = self.__size[1] - 2
        for line_no, line in enumerate(self.__box):
            self.__pad.move(line_no, 0)
            self.__pad.addnstr(line, width)

        for colorpair, blocks in countblocks.items():
            for block in blocks:
                subpad = self.__pad.subpad(1, block[2], block[0], block[1])
                subpad.bkgd(colorpair | curses.A_BOLD)

        for group in self.__name_blocks.values():
            for block in group:
                block.bkgd(curses.A_DIM)

        self.set_selected(self.__selected)

    def set_selected(self, name: str | None):
        if name is not None and name not in self.__name_blocks:
            raise ValueError(f"No character {name}")
        if self.__selected is not None:
            for block in self.__name_blocks[self.__selected]:
                block.bkgd(curses.A_DIM)
        self.__selected = name
        if self.__selected is not None:
            for block in self.__name_blocks[self.__selected]:
                block.bkgd(curses.A_BOLD)
        self.refresh()

    def render(self, window: curses.window):
        curses.textpad.rectangle(window, self.__pos[0], self.__pos[1], self.__pos[0] + self.__size[0], self.__pos[1] + self.__size[1])
        window.move(self.__pos[0], self.__pos[1] + 2)
        window.addstr("Initiative", curses.A_BOLD)
        window.refresh()
        self.refresh()

    def refresh(self):
        self.__pad.refresh(0, 0, self.__pos[0] + 1, self.__pos[1] + 1, self.__pos[0] + self.__size[0] - 1, self.__pos[1] + self.__size[1] - 1)

    @property
    def size(self) -> tuple[int, int]:
        return self.__size


# TODO: Accept pre-built encounters
def _run_encounter(stdscr: curses.window):
    curses.use_default_colors()
    curses.curs_set(0)

    init_win = InitiativeWindow(
        [InitiativeCount(characters=["Player 1", "Player 2"], count=20, is_enemy=False), InitiativeCount(characters=["Enemy 1"], count=15, is_enemy=True)],
        (15, 25),
    )

    stdscr.refresh()
    init_win.render(stdscr)

    chars = ["Player 1", "Player 2", "Enemy 1"]
    selected = 0
    init_win.set_selected(chars[selected])

    running = True
    mode = 0  # 0 = global, 1 = command
    while running:
        try:
            ch = stdscr.getch()
        except KeyboardInterrupt:
            break
        match mode:
            case 0:
                if ch == ord('n'):
                    selected = (selected + 1) % len(chars)
                    init_win.set_selected(chars[selected])
                elif ch == ord('p'):
                    selected = (selected - 1) % len(chars)
                    init_win.set_selected(chars[selected])


def run_encounter(_):
    curses.wrapper(_run_encounter)

