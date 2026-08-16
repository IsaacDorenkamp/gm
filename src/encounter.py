import bisect
import curses
from dataclasses import dataclass
from typing import Generator

from models import Action, Character, InitiativeKey
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


# TODO: Accept pre-built encounters
def _run_encounter(stdscr: curses.window):
    encounter = Encounter()

    tracker_lines: list[str]
    tracker_height: int
    tracker_width: int

    command_start: tuple[int, int] = (0, 0)
    command = ''

    running = True

    def update_tracker():
        # first: calculate size of initiative tracker
        nonlocal tracker_lines
        nonlocal tracker_height
        nonlocal tracker_width
        tracker_lines = ["[%02d] %s" % (group.count, ', '.join(group.characters)) for group in encounter.initiative_groups]
        tracker_height = len(tracker_lines)
        tracker_width = max(len(line) for line in tracker_lines) if tracker_lines else 0

        nonlocal command_start
        command_start = tracker_height + 1, 0

    def command_write(ch: str):
        nonlocal command
        command += ch
        stdscr.move(command_start[0], command_start[1] + len(command))
        stdscr.addch(ch)
        stdscr.refresh()

    def command_run():
        nonlocal command

        if command == "/exit":
            nonlocal running
            running = False

        command = ""

        stdscr.move(*command_start)
        stdscr.clrtoeol()
        stdscr.refresh()

    def update_all():
        update_tracker()

    update_all()

    mode = 0  # 0 = global, 1 = command
    while running:
        ch = stdscr.getch()
        curses.beep()
        match mode:
            case 0:
                if ch == ord('/'):
                    mode = 1
                    command_write('/')
            case 1:
                if ch == ord('\n'):
                    command_run()
                else:
                    command_write(chr(ch))

