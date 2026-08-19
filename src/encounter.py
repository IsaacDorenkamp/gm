import bisect
from collections import defaultdict
import curses
import curses.textpad
from dataclasses import dataclass
from typing import Generator

import gcurses
import initiative
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


# TODO:
# - Avoid assigning ally_pair and enemy_pair multiple times
class InitiativeWindow:
    ALLY_COLOR  = curses.COLOR_GREEN
    ENEMY_COLOR = curses.COLOR_RED

    __pos: tuple[int, int]
    __size: tuple[int, int]
    __box: gcurses.WrapBox
    __pad: curses.window

    __name_blocks: dict[str, list[curses.window]]
    __count_blocks: dict[InitiativeKey, list[curses.window]]
    __counts: dict[InitiativeKey, int]
    __name_keys: dict[str, InitiativeKey]

    __selected: str | None
    __active_count: InitiativeKey | None

    __parent: curses.window
    __scroll: int

    def __init__(self, entries: list[InitiativeCount], parent: curses.window, size: tuple[int, int], pos: tuple[int, int] = (0, 0)):
        self.__pos = pos
        self.__size = size
        self.__parent = parent
        self.__box = gcurses.WrapBox(size[1] - 2)
        self.__counts = {}
        self.__name_keys = {}
        self.__name_blocks = {}
        self.__selected = None
        self.__active_count = None
        self.__scroll = 0
        self.__generate(entries)

    def __generate(self, entries: list[InitiativeCount]):
        ally_pair = gcurses.pair(self.ALLY_COLOR, -1)
        enemy_pair = gcurses.pair(self.ENEMY_COLOR, -1)

        self.__counts.clear()
        self.__name_blocks.clear()
        self.__box.clear()

        blocks = defaultdict(list)
        count_blocks = defaultdict(list)
        for entry in entries:
            key = InitiativeKey(count=entry.count, is_enemy=entry.is_enemy)
            self.__counts[key] = self.__box.line
            count_blocks[key].extend(self.__box.write("[%02d] " % entry.count))
            self.__box.indent = 5
            for idx, name in enumerate(entry.characters):
                self.__name_keys[name] = key
                if idx > 0:
                    self.__box.write(', ')
                for block in self.__box.write(name):
                    blocks[name].append(block)
            self.__box.indent = 0
            self.__box.linebreak()

        self.__pad = curses.newpad(self.__box.nlines, self.__box.width)
        for name, text_blocks in blocks.items():
            self.__name_blocks[name] = [self.__pad.subpad(1, block[2], block[0], block[1]) for block in text_blocks]

        for line_no, line in enumerate(self.__box):
            self.__pad.move(line_no, 0)
            try:
                self.__pad.addnstr(line, self.__box.width)
            except curses.error:
                pass

        self.__count_blocks = { key: [self.__pad.subpad(1, block[2], block[0], block[1]) for block in blocks] for key, blocks in count_blocks.items() }
        for key, blocks in count_blocks.items():
            colorpair = enemy_pair if key.is_enemy else ally_pair
            for block in blocks:
                subpad = self.__pad.subpad(1, block[2], block[0], block[1])
                subpad.bkgd(colorpair | curses.A_BOLD | curses.A_DIM)

        for group in self.__name_blocks.values():
            for block in group:
                block.bkgd(curses.A_DIM)

        self.set_selected(self.__selected)

    def scroll_to(self, name: str):
        if name not in self.__name_blocks:
            raise ValueError(f"No character {name}")

        blocks = self.__name_blocks[name]
        min_y = self.__box.nlines - 1
        max_y = 0
        for block in blocks:
            top_y, _ = block.getparyx()
            height, _ = block.getmaxyx()
            bot_y = top_y + height - 1
            min_y = min(top_y, min_y)
            max_y = max(bot_y, max_y)

        scr_top_y = self.__scroll
        scr_bot_y = self.__scroll + self.size[0] - 2

        if min_y < scr_top_y:
            self.__scroll = min_y
        elif max_y > scr_bot_y:
            self.__scroll = max_y - (self.size[0] - 2)

        self.refresh()

    def set_selected(self, name: str | None):
        if name is not None and name not in self.__name_blocks:
            raise ValueError(f"No character {name}")
        if self.__selected is not None:
            for block in self.__name_blocks[self.__selected]:
                block.bkgd(curses.A_DIM)
        self.__selected = name
        if self.__selected is not None:
            count = self.__name_keys[self.__selected]
            self.__set_active_count(count)
            for block in self.__name_blocks[self.__selected]:
                block.bkgd(curses.A_BOLD)
            self.scroll_to(self.__selected)
        else:
            self.__set_active_count(None)
        self.refresh()

    def __set_active_count(self, count: InitiativeKey | None):
        ally_pair = gcurses.pair(self.ALLY_COLOR, -1)
        enemy_pair = gcurses.pair(self.ENEMY_COLOR, -1)
        if self.__active_count is not None:
            for block in self.__count_blocks[self.__active_count]:
                block.bkgd((enemy_pair if self.__active_count.is_enemy else ally_pair) | curses.A_DIM)
        self.__active_count = count
        if self.__active_count is not None:
            for block in self.__count_blocks[self.__active_count]:
                block.bkgd((enemy_pair if self.__active_count.is_enemy else ally_pair) | curses.A_BOLD)


    def render(self):
        curses.textpad.rectangle(self.__parent, self.__pos[0], self.__pos[1], self.__pos[0] + self.__size[0], self.__pos[1] + self.__size[1])
        self.__parent.move(self.__pos[0], self.__pos[1] + 2)
        self.__parent.addstr("Initiative", curses.A_BOLD)
        self.__parent.refresh()
        self.refresh()

    def refresh(self):
        self.__pad.refresh(self.__scroll, 0, self.__pos[0] + 1, self.__pos[1] + 1, self.__pos[0] + self.__size[0] - 1, self.__pos[1] + self.__size[1] - 1)

    def set_initiative(self, initiative: list[InitiativeCount]):
        self.__generate(initiative)
        # deselect if name is missing
        if self.__selected is not None and self.__selected not in self.__name_blocks:
            self.__selected = None
        else:
            self.set_selected(self.__selected)

    @property
    def size(self) -> tuple[int, int]:
        return self.__size


# TODO: Accept pre-built encounters
def _run_encounter(stdscr: curses.window):
    curses.use_default_colors()
    curses.curs_set(0)

    roster = initiative.Roster()
    characters = []
    for i in range(20):
        c = Character(max_hp=10, hp=(0 if i % 10 == 7 else 10), temp_hp=0, name=f"Character {i + 1}", is_enemy=bool(i % 3))
        roster.add_character(c, i + 1)
        characters.append(c)
    init_win = InitiativeWindow(
        roster.counts,
        stdscr,
        (15, 25),
    )
    command_box = gcurses.LineEdit((16, 0), 35)

    stdscr.refresh()
    init_win.render()

    chars = roster.characters
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
                elif ch == ord('/'):
                    curses.curs_set(1)
                    mode = 1
                    command_box.append('/')
            case 1:
                command_box.keystroke(ch)


def run_encounter(_):
    curses.wrapper(_run_encounter)

