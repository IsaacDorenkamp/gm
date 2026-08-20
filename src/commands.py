from __future__ import annotations
import abc
import enum
from functools import cached_property
import io
import typing


T = typing.TypeVar("T")


class Argument(typing.Generic[T], metaclass=abc.ABCMeta):
    __name: str

    def __init__(self, name: str):
        self.__name = name

    @property
    def name(self) -> str:
        return self.__name

    @abc.abstractmethod
    def read(self, string: str) -> tuple[T, str]:
        """
        Parse a value of type T from the string, starting from the
        beginning. If successful, return a tuple containing the
        value and the portion of the string which remains unparsed.
        Otherwise, raise a ValueError.

        :param string: The string from which to read a value
        :return: A tuple containing the parsed value and the unparsed
        remainder of the string.
        :raises: ValueError, if no value can be read from the string.
        """
        raise NotImplementedError()

    @property
    def usage(self) -> str:
        return self.name


class RemainderArg(Argument[str]):
    def __init__(self, name: str):
        super().__init__(name)

    def read(self, string: str) -> tuple[str, str]:
        return string.strip(), ''

    @property
    def usage(self) -> str:
        return f"{self.name}(str)..."


class StringArg(Argument[str]):
    def __init__(self, name: str):
        super().__init__(name)

    def read(self, string: str) -> tuple[str, str]:
        bookend = None
        if string[0] in ('"', "'"):
            bookend = string[0]

        result = io.StringIO()
        idx = -1
        for idx, ch in enumerate(string):
            if ch == bookend and idx > 0:
                bookend = None
                break
            elif ch == bookend:
                continue
            elif ch == ' ' and bookend is None:
                idx -= 1
                break
            else:
                result.write(ch)

        if bookend is not None:
            raise ValueError("Unmatched quote %s" % bookend)

        return result.getvalue(), string[idx+1:]

    @property
    def usage(self) -> str:
        return f"{self.name}(str)"


class ChoiceArg(StringArg):
    __choices: list[str]
    def __init__(self, name: str, choices: list[str]):
        super().__init__(name)
        self.__choices = choices

    def read(self, string: str) -> tuple[str, str]:
        value, remainder = super().read(string)
        if value not in self.__choices:
            raise ValueError(f"'{self.name}' must be one of: {', '.join(self.__choices)}; got '{value}'")
        return value, remainder

    @property
    def usage(self) -> str:
        return f"{self.name}({"|".join(self.__choices)})"


class IntArg(Argument[int]):
    __min: int | None
    __max: int | None
    __base: int

    def __init__(self, name: str, min: int | None = None, max: int | None = None, base: int = 10):
        super().__init__(name)
        if min is not None and max is not None and min > max:
            raise ValueError("min cannot be greater than max!")
        self.__min = min
        self.__max = max
        self.__base = base

        if base > 10 and base != 16:
            raise ValueError("base must be 2-10 or 16")
        elif base <= 1:
            raise ValueError("base must be 2-10 or 16")

    @cached_property
    def digits(self):
        if self.__base <= 10:
            return '0123456789'[:self.__base]
        else:
            return '0123456789abcdefABCDEF'

    def read(self, string: str) -> tuple[int, str]:
        result = io.StringIO()
        idx = -1
        for idx, ch in enumerate(string):
            if ch in self.digits:
                result.write(ch)
            elif ch.isspace():
                break
            else:
                raise ValueError(f"{self.name} must only contain digits for base {self.__base}")
        else:
            idx += 1

        value = int(result.getvalue(), base=self.__base)
        if self.__min is not None and value < self.__min:
            raise ValueError(f"{self.name} must not be less than {self.__min}")
        elif self.__max is not None and value > self.__max:
            raise ValueError(f"{self.name} must not be more than {self.__max}")

        return value, string[idx:]

    @property
    def usage(self) -> str:
        return f"{self.name}(int)"


class ArgType(enum.Enum):
    Remainder = enum.auto()
    String = enum.auto()
    Choice = enum.auto()
    Int = enum.auto()


class CommandParseError(ValueError):
    """
    An error to raise when something goes wrong while parsing a command.
    """

    command: Command | None
    """
    If a particular command was identified as the parsed command, this
    represents that command. Otherwise, if a parse error occurred before
    a command could be identified, it is None.
    """

    def __init__(self, msg: str, command: Command | None = None):
        super().__init__(msg)
        self.command = command


class Command:
    __name: str
    __args: list[Argument]

    def __init__(self, name: str):
        self.__name = name
        self.__args = []

    @property
    def name(self) -> str:
        return self.__name

    def add_argument(self, arg_type: ArgType, name: str, *args, **kwargs):
        if self.__args and isinstance(self.__args[-1], RemainderArg):
            raise ValueError("cannot add arguments after a Remainder argument!")
        match arg_type:
            case ArgType.Remainder:
                arg = RemainderArg(name, *args, **kwargs)
            case ArgType.String:
                arg = StringArg(name)
            case ArgType.Choice:
                arg = ChoiceArg(name, *args, **kwargs)
            case ArgType.Int:
                arg = IntArg(name, *args, **kwargs)
        self.__args.append(arg)

    def parse_args(self, args: str) -> tuple[dict[str, typing.Any], str]:
        args = args.strip()
        values = {}
        for arg in self.__args:
            while args and args[0].isspace():
                args = args[1:]
            if not args:
                raise ValueError(f"missing argument '{arg.name}'")
            value, args = arg.read(args)
            values[arg.name] = value
        return values, args

    @property
    def usage(self) -> str:
        usage = self.name
        for arg in self.__args:
            usage += " " + arg.usage
        return usage


class CommandParser:
    __commands: dict[str, Command]

    def __init__(self):
        self.__commands = {}

    def add_command(self, command: Command):
        self.__commands[command.name] = command

    def parse_command(self, string: str) -> tuple[str, dict[str, typing.Any]]:
        if not string:
            raise CommandParseError("command cannot be empty")

        if string[0] != '/':
            raise CommandParseError("command must begin with '/'")

        string = string[1:]
        what_remains = string.split(' ', maxsplit=1)
        command_str = what_remains[0]
        if command_str not in self.__commands:
            raise CommandParseError(f"no command '{command_str}'")

        command = self.__commands[command_str]
        if len(what_remains) == 2:
            arg_string = what_remains[1]
        else:
            arg_string = ""

        try:
            arguments, remainder = command.parse_args(arg_string)
        except ValueError as ve:
            raise CommandParseError(str(ve), command=command)
        if remainder:
            raise CommandParseError("received more arguments than expected", command=command)

        return command.name, arguments

