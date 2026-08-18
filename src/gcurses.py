import curses
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
                self.__pushline()
                word = word[remaining - 1:]
                yield block
                remaining = self.__width - self.__column
        elif len(word) > remaining:
            # word can fit on a single line, but not in the current one
            self.__pushline()
            block = (self.__line, self.__column, len(word))
            self.__text += word
            self.__column = len(word)
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

