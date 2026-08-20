import curses
import string
from typing import Generator


__nextpair: int = 1
__pairs: dict[tuple[int, int], int] = {}


def pair(fg: int, bg: int) -> int:
    global __nextpair
    global __pairs

    key = fg, bg
    if key not in __pairs:
        curses.init_pair(__nextpair, fg, bg)
        __pairs[key] = __nextpair
        __nextpair += 1

    return curses.color_pair(__pairs[key])


class WrapBox:
    __width: int
    __line: int
    __column: int

    __text: str
    __lines: list[str]
    __indent: int

    def __init__(self, line_width: int):
        self.__width = line_width
        self.__line = 0
        self.__column = 0
        self.__text = ""
        self.__lines = []
        self.__indent = 0

    def clear(self):
        self.__line = 0
        self.__column = 0
        self.__text = ""
        self.__lines.clear()
        self.__indent = 0

    def write(self, text: str) -> list[tuple[int, int, int]]:
        blocks = []
        for idx, word in enumerate(text.split(' ')):
            if idx > 0:
                blocks.append(self.__write_char(' '))
            if word:
                blocks.extend(self.__write_word(word))
        return blocks

    def linebreak(self):
        self.__pushline()

    def __write_char(self, ch: str) -> tuple[int, int, int]:
        if len(ch) != 1:
            raise ValueError("ch must only be one character long!")
        if self.__column == self.__width:
            self.__pushline()
        block = (self.__line, self.__column, 1)
        self.__column += 1
        self.__text += ch
        return block

    def __write_word(self, word: str) -> Generator[tuple[int, int, int], None, None]:
        remaining = self.__width - self.__column
        if len(word) > (self.__width - self.__indent):
            # word won't fit, even on an empty line - so we'll split the word.
            while word:
                if len(word) > remaining:
                    portion = word[:remaining - 1] + "-"
                else:
                    portion = word
                block = (self.__line, self.__column, len(portion))
                self.__text += portion
                if portion != word:
                    self.__pushline()
                word = word[remaining - 1:]
                yield block
                remaining = self.__width - self.__column
        elif len(word) > remaining:
            # word can fit on a single line, but not in the current one
            self.__pushline()
            block = (self.__line, self.__column, len(word))
            self.__text += word
            self.__column += len(word)
            yield block
        else:
            block = (self.__line, self.__column, len(word))
            self.__text += word
            self.__column += len(word)
            yield block

    def __pushline(self):
        self.__lines.append(self.__text)
        self.__text = " " * self.__indent
        self.__line += 1
        self.__column = self.__indent

    @property
    def indent(self) -> int:
        return self.__indent

    @indent.setter
    def indent(self, indent: int):
        self.__indent = indent

    @property
    def line(self) -> int:
        return self.__line

    @property
    def nlines(self) -> int:
        if self.__text:
            return len(self.__lines) + 1
        else:
            return len(self.__lines)

    @property
    def width(self) -> int:
        return self.__width

    def __iter__(self) -> Generator[str, None, None]:
        yield from self.__lines
        if self.__text:
            yield self.__text


class LineEdit:
    __window: curses.window
    __width: int
    __text: str
    __offset: int

    def __init__(self, pos: tuple[int, int], width: int, text: str = ""):
        self.__window = curses.newwin(1, width, *pos)
        self.__width = width
        self.__text = ""
        self.__offset = 0
        self.append(text)

    def clear(self):
        self.__text = ""
        self.__window.erase()
        self.__window.refresh()
        self.__offset = 0

    def append(self, text: str):
        self.__text += text
        if len(self.__text) > self.__width - 1:
            portion = self.__text[len(self.__text) - (self.__width - 1):]
        else:
            portion = text
        self.__window.erase()
        self.__window.addnstr(portion, self.__width - 1)
        self.__window.refresh()

    def putchar(self, ch: str):
        if len(ch) != 1:
            raise ValueError("ch must be exactly 1 character")
        relpos = self.__window.getyx()[1]
        index = relpos + self.__offset
        self.__text = self.__text[:index] + ch + self.__text[index:]
        if relpos == self.__width:
            self.__window.insch(ch)
            self.__window.move(0, 0)
            self.__window.delch()
            self.__window.move(0, self.__width - 1)
        else:
            self.__window.insch(ch)
            self.mvcursor(index + 1)
        self.__window.refresh()

    def delchar(self):
        pos = self.__window.getyx()[1]
        index = pos + self.__offset
        if index > 0:
            to_remove = index - 1
            self.__text = self.__text[:to_remove] + self.__text[to_remove+1:]
            if pos == 0:
                self.__move_offset(self.__offset - 1)
            else:
                self.__window.move(0, pos - 1)
                self.__window.delch()
                self.__window.refresh()

    def mvcursor(self, pos: int):
        if pos < 0 or pos > len(self.__text):
            raise ValueError(f"Position {pos} out of bounds")

        max_pos = self.__offset + self.__width - 1
        if pos < self.__offset:
            self.__move_offset(pos)
            self.__window.move(0, 0)
        elif pos > max_pos:
            self.__move_offset(pos - self.__width + 1)
        else:
            adjusted = pos - self.__offset
            self.__window.move(0, adjusted)

        self.__window.refresh()

    def __move_offset(self, offset: int):
        self.__offset = offset
        self.__redraw()

    def __redraw(self):
        self.__window.erase()
        portion = self.__text[self.__offset:self.__offset+self.__width]
        try:
            self.__window.addnstr(portion, self.__width)
        except curses.error:
            pass

    def keystroke(self, key: int) -> bool:
        match key:
            case 127:
                self.delchar()
            case curses.KEY_BACKSPACE:
                self.delchar()
            case curses.KEY_RIGHT:
                pos = self.__window.getyx()[1]
                abs_pos = pos + self.__offset
                self.mvcursor(min(abs_pos + 1, len(self.__text)))
            case curses.KEY_LEFT:
                pos = self.__window.getyx()[1]
                abs_pos = pos + self.__offset
                self.mvcursor(max(0, abs_pos - 1))
            case _:
                ch = chr(key)
                if ch in string.printable:
                    self.putchar(ch)
                else:
                    return False

        return True

    @property
    def text(self) -> str:
        return self.__text

