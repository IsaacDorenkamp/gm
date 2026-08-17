import bisect
from collections import defaultdict
import curses
import curses.textpad
from dataclasses import dataclass
from typing import Generator

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


def run_encounter(_):
    curses.wrapper(_run_encounter)


class InitiativeWindow:
    __size: tuple[int, int]
    __pad: curses.window

    # block: tuple[begin_y, begin_x, columns]
    __blocks: dict[str, list[tuple[int, int, int]]]
    __counts: dict[int, int]
    __lines: list[str]

    def __init__(self, entries: list[InitiativeCount]):
        self.__generate(entries)

    def __generate(self, entries: list[InitiativeCount], line_width: int = 25):
        self.__counts = {}
        blocks = defaultdict(list)
        line    = 1
        column  = 1
        lines   = [" Initiative"]
        text    = " "
        for entry in entries:
            # first, initiative count
            self.__counts[entry.count] = line
            text += f"[%02d] " % entry.count
            column += len(text)
            words = ", ".join(entry.characters).split(" ")
            while len(words):
                word = words[0]
                needed_columns = len(word)
                remaining = line_width - column
                # the word is too long to hold on a single
                # line, no matter what, so take as much of
                # the word as we can
                if needed_columns > remaining:
                    portion = words[0][:(line_width - column + 1)]
                    words[0] = words[0][line_width:]
                elif needed_columns > remaining:
                    # goto next line in order to fit it
                    lines.append(text)
                    text = " "
                    column = 1
                    line += 1
                    continue
                else:
                    portion = words.pop(0)

                blocks[word].append((line, column, len(portion)))
                text += portion
                column += len(portion)

                if column < line_width:
                    text += " "
                    column += 1
                else:
                    lines.append(text)
                    text = " "
                    column = 1
                    line += 1

            if text != " ":
                lines.append(text)
                line += 1
                column = 1
                text = " "

        if text != " ":
            lines.append(text)

        height = len(lines)

        self.__size = (height, line_width)
        self.__pad = curses.newpad(height, line_width)
        self.__blocks = dict(blocks)
        self.__lines = lines

        for idx, line in enumerate(self.__lines):
            self.__pad.move(idx, 0)
            self.__pad.addnstr(line, line_width)

    def render_to(self, target: tuple[int, int, int, int]):
        self.__pad.refresh(0, 0, *target)

    @property
    def size(self) -> tuple[int, int]:
        return self.__size

    # TODO: block highlighting


# TODO: Accept pre-built encounters
def _run_encounter(stdscr: curses.window):
    encounter = Encounter()

    init_win = InitiativeWindow([InitiativeCount(characters=["Player 1", "Player 2"], count=20, is_enemy=False), InitiativeCount(characters=["Enemy 1"], count=15, is_enemy=True)])
    resource_win = curses.newpad(35, 35)
    command_win = curses.newpad(1, 50)

    curses.textpad.rectangle(stdscr, 0, 0, 17, 27)
    stdscr.refresh()

    init_win.render_to((1, 1, 10, 25))

    running = True
    mode = 0  # 0 = global, 1 = command
    while running:
        try:
            ch = stdscr.getch()
        except KeyboardInterrupt:
            break
        match mode:
            case 0:
                if ch == ord('/'):
                    mode = 1
                    #command_write('/')
            case 1:
                if ch == ord('\n'):
                    command_run()
                else:
                    #command_write(chr(ch))
                    ...

