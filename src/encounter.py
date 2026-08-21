from collections import defaultdict
import curses
import curses.textpad

import commands
import gcurses
import initiative
from models import Action, Character, InitiativeCount, InitiativeKey
import repo


class Encounter:
    __roster: initiative.Roster
    __characters: dict[str, Character]
    __actions: dict[str, int]
    __active: tuple[int, str]

    # log
    __action_log: list[tuple[str, Action]]

    def __init__(self):
        self.__roster = initiative.Roster()
        self.__characters = {}
        self.__actions = {}
        self.__active = (-1, "")

    @property
    def roster(self) -> initiative.Roster:
        return self.__roster

    def add_character(self, character: Character, count: int):
        self.__roster.add_character(character.name, character.is_enemy, count)
        self.__characters[character.name] = character
        self.__actions[character.name] = 3

        if self.__active[0] != -1:
            new_index = self.__roster.characters.index(self.__active[1])
            self.__active = (new_index, self.__active[1])

    def remove_character(self, character: str):
        if character in self.__characters:
            current_name = self.__active[1]
            del self.__characters[character]
            del self.__actions[character]
            self.__roster.remove_character(character)
            try:
                index = self.__roster.characters.index(current_name)
                self.__active = (index, current_name)
            except ValueError:
                self.__active = (-1, "")
        else:
            raise ValueError(f"No character '{character}'")

    def begin(self) -> str:
        if self.__active[0] == -1:
            if self.__roster.ncounts:
                self.__active = (0, self.__roster.characters[0])
                self.__actions[self.__active[1]] = 3
                return self.__active[1]
            else:
                raise ValueError("No characters are in initiative!")
        else:
            raise ValueError("Already started!")

    def act(self, action: Action):
        char = self.active_character
        if char is None:
            raise ValueError("No active character.")
        if self.__actions[char.name] >= action.cost:
            self.__actions[char.name] -= action.cost
            # TODO: copy action instance?
            self.__action_log.append((char.name, action))
        else:
            # TODO: better messaging
            raise ValueError("Not enough actions to do that!")

    def get_actions(self, character: str) -> int:
        return self.__actions[character]

    @property
    def active_character(self) -> Character | None:
        if self.__active[0] == -1:
            return None

        return self.__characters[self.__active[1]]

    def next_turn(self):
        next_index = (self.__active[0] + 1) % self.__roster.ncounts
        self.__active = (next_index, self.__roster.characters[next_index])

    def previous_turn(self):
        next_index = (self.__active[0] - 1) % self.__roster.ncounts
        self.__active = (next_index, self.__roster.characters[next_index])

    def update_character_hp(self, name: str, diff: int):
        char = self.__characters[name]
        char.update_hp(diff)

    def set_character_hp(self, name: str, hp: int):
        char = self.__characters[name]
        char.set_hp(hp)


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

    __ally_attr: int
    __enemy_attr: int

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

        self.__ally_attr = gcurses.pair(self.ALLY_COLOR, -1)
        self.__enemy_attr = gcurses.pair(self.ENEMY_COLOR, -1)

        self.__generate(entries)

    def __generate(self, entries: list[InitiativeCount]):
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

        self.__pad = curses.newpad(self.__box.nlines or 1, self.__box.width or 1)
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
            colorpair = self.__enemy_attr if key.is_enemy else self.__ally_attr
            for block in blocks:
                subpad = self.__pad.subpad(1, block[2], block[0], block[1])
                subpad.bkgd(colorpair | curses.A_BOLD | curses.A_DIM)

        for group in self.__name_blocks.values():
            for block in group:
                block.bkgd(curses.A_DIM)

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
        if self.__active_count is not None:
            for block in self.__count_blocks[self.__active_count]:
                block.bkgd((self.__enemy_attr if self.__active_count.is_enemy else self.__ally_attr) | curses.A_DIM)
        self.__active_count = count
        if self.__active_count is not None:
            for block in self.__count_blocks[self.__active_count]:
                block.bkgd((self.__enemy_attr if self.__active_count.is_enemy else self.__ally_attr) | curses.A_BOLD)

    def render(self):
        curses.textpad.rectangle(self.__parent, self.__pos[0], self.__pos[1], self.__pos[0] + self.__size[0], self.__pos[1] + self.__size[1])
        self.__parent.move(self.__pos[0], self.__pos[1] + 2)
        self.__parent.addstr("Initiative", curses.A_BOLD)
        self.__parent.refresh()
        self.refresh()

    def refresh(self):
        self.__pad.refresh(self.__scroll, 0, self.__pos[0] + 1, self.__pos[1] + 1, self.__pos[0] + self.__size[0] - 1, self.__pos[1] + self.__size[1] - 1)

    def set_initiative(self, initiative: list[InitiativeCount]):
        self.__pad.erase()
        self.refresh()
        self.__generate(initiative)
        # deselect if name is missing
        if self.__selected is not None and self.__selected not in self.__name_blocks:
            self.__selected = None
            self.__active_count = None
            self.refresh()
        else:
            self.set_selected(self.__selected)

    @property
    def size(self) -> tuple[int, int]:
        return self.__size


class StatusWindow:
    __window: curses.window

    character: Character | None
    actions: int

    def __init__(self, pos: tuple[int, int], character: Character | None = None, actions: int = 3):
        self.__window = curses.newwin(6, 30, *pos)
        self.character = character
        self.actions = actions

    def hide(self):
        self.__window.erase()
        self.__window.refresh()

    def render(self):
        self.__window.erase()
        self.__window.border()
        self.__window.move(0, 1)
        self.__window.addstr("Status")
        self.__window.move(1, 1)
        self.__window.addnstr(f"Name: {self.character.name if self.character else ""}", 28)
        self.__window.move(2, 1)
        self.__window.addstr("Actions: ")
        for _ in range(self.actions):
            self.__window.addstr("\u25C6  ")

        for _ in range(3 - self.actions):
            self.__window.addstr("\u25C7  ")
        self.__window.move(3, 1)
        self.__window.addstr("HP: ")
        self.__window.move(4, 1)
        self.__window.addstr("Temp HP: ")
        self.__window.refresh()


# TODO: Accept pre-built encounters
def _run_encounter(stdscr: curses.window):
    curses.use_default_colors()
    curses.curs_set(0)

    stdheight, stdwidth = stdscr.getmaxyx()

    encounter = Encounter()
    init_win = InitiativeWindow(
        encounter.roster.counts,
        stdscr,
        (stdheight - 3, 30),
    )
    status_win = StatusWindow((0, 31))

    stdscr.refresh()
    init_win.render()

    command_box = gcurses.LineEdit((stdheight - 1, 0), stdwidth)
    status_bar = gcurses.StaticText((stdheight - 2, 0), stdwidth, "Ready")

    status_attr = gcurses.pair(curses.COLOR_BLACK, curses.COLOR_GREEN)
    error_attr = gcurses.pair(curses.COLOR_BLACK, curses.COLOR_RED) | curses.A_BOLD
    status_bar.bkgd(status_attr)

    parser = commands.CommandParser()

    add_cmd = commands.Command("add")
    add_cmd.add_argument(commands.ArgType.Choice, "type", choices=["player", "enemy", "npc"])
    add_cmd.add_argument(commands.ArgType.Int, "count")
    add_cmd.add_argument(commands.ArgType.Remainder, "name")

    rm_cmd = commands.Command("rm")
    rm_cmd.add_argument(commands.ArgType.Choice, "type", choices=["player", "enemy", "npc"])
    rm_cmd.add_argument(commands.ArgType.Remainder, "name")

    exit_cmd = commands.Command("exit")

    parser.add_command(add_cmd)
    parser.add_command(rm_cmd)
    parser.add_command(exit_cmd)

    def success(string: str):
        status_bar.text = string
        status_bar.bkgd(status_attr)

    def error(string: str):
        status_bar.text = string
        status_bar.bkgd(error_attr)

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
                    if encounter.active_character:
                        encounter.next_turn()
                        init_win.set_selected(encounter.active_character.name)
                        name = encounter.active_character.name
                    else:
                        try:
                            name = encounter.begin()
                            init_win.set_selected(name)
                        except ValueError as err:
                            error(str(err))
                            continue
                    status_win.character = encounter.active_character
                    status_win.actions = encounter.get_actions(name)
                    status_win.render()
                elif ch == ord('p'):
                    if encounter.active_character:
                        encounter.previous_turn()
                        init_win.set_selected(encounter.active_character.name)
                        status_win.character = encounter.active_character
                        status_win.actions = encounter.get_actions(encounter.active_character.name)
                        status_win.render()
                elif ch == ord('/'):
                    curses.curs_set(1)
                    command_box.append('/')
                    mode = 1
            case 1:
                if ch == 10:
                    text = command_box.text
                    command_box.clear()
                    curses.curs_set(0)

                    try:
                        command, args = parser.parse_command(text)
                    except commands.CommandParseError as err:
                        if err.command:
                            error(f"usage: /{err.command.usage}")
                        else:
                            error(f"Error: {err}")
                        mode = 0
                        continue

                    match command:
                        case "add":
                            char_type = args["type"]
                            count = args["count"]
                            name = args["name"]

                            if char_type == "player":
                                try:
                                    player = repo.players.get(name)
                                except repo.RepoError as re:
                                    error(f"Error: {str(re)}")
                                    continue

                                char = Character(name=player.name, max_hp=player.max_hp, hp=player.max_hp, temp_hp=0, is_enemy=False)
                            else:
                                char = Character(name=name, max_hp=1, hp=1, temp_hp=0, is_enemy=char_type == "enemy")

                            try:
                                encounter.add_character(char, count)
                                init_win.set_initiative(encounter.roster.counts)
                                success(f"Added {char.name} to initiative.")
                            except ValueError as err:
                                error(f"Error: {err}")
                        case "rm":
                            char_type, name = args["type"], args["name"]

                            if char_type == "player":
                                try:
                                    player = repo.players.get(name)
                                except repo.RepoError as re:
                                    error(f"Error: {str(re)}")
                                    continue
                                name = player.name

                            try:
                                encounter.remove_character(name)
                                init_win.set_initiative(encounter.roster.counts)
                                success(f"Removed {name} from initiative.")
                            except ValueError as err:
                                error(f"Error: {err}")
                        case "exit":
                            running = False

                    mode = 0
                else:
                    command_box.keystroke(ch)


def run_encounter(_):
    curses.wrapper(_run_encounter)

