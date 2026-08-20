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


class RemainderArg(Argument[str]):
    def __init__(self, name: str):
        super().__init__(name)

    def read(self, string: str) -> tuple[str, str]:
        return string.strip(), ''


class StringArg(Argument[str]):
    def __init__(self, name: str):
        super().__init__(name)

    def read(self, string: str) -> tuple[str, str]:
        bookend = None
        if string[0] in ('"', "'"):
            bookend = string[0]

        result = io.StringIO()
        idx = -1
        for idx, ch in enumerate(string[1:] if bookend else string):
            if (
                ch == bookend or
                (ch == ' ' and bookend is None)
            ):
                bookend = None
                break
            else:
                result.write(ch)

        if bookend is not None:
            raise ValueError("Unmatched quote %s" % bookend)

        return result.getvalue(), string[idx+1:]


class ChoiceArg(StringArg):
    __choices: set[str]
    def __init__(self, name: str, choices: set[str]):
        super().__init__(name)
        self.__choices = choices

    def read(self, string: str) -> tuple[str, str]:
        value, remainder = super().read(string)
        if value not in self.__choices:
            raise ValueError(f"'{self.name}' must be one of: {', '.join(self.__choices)}; got '{value}'")
        return value, remainder


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
                raise ValueError(f"{self.name} must only contain these digits: {self.digits}")

        if idx == -1:
            raise ValueError(f"{self.name} cannot be empty")

        value = int(result.getvalue(), base=self.__base)
        if self.__min is not None and value < self.__min:
            raise ValueError(f"{self.name} must not be less than {self.__min}")
        elif self.__max is not None and value > self.__max:
            raise ValueError(f"{self.name} must not be more than {self.__max}")

        return value, string[idx:]


class ArgType(enum.Enum):
    Remainder = enum.auto()
    String = enum.auto()
    Choice = enum.auto()
    Int = enum.auto()


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
            raise ValueError("Cannot add arguments after a Remainder argument!")
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

    def parse_args(self, args: str) -> dict[str, typing.Any]:
        args = args.strip()
        values = {}
        for arg in self.__args:
            while args and args[0].isspace():
                args = args[1:]
            value, args = arg.read(args)
            values[arg.name] = value
        return values


class CommandParser:
    __commands: dict[str, Command]

    def __init__(self):
        self.__commands = {}

    def add_command(self, command: Command):
        self.__commands[command.name] = command

    def parse_command(self, string: str) -> tuple[str, dict[str, typing.Any]]:
        if not string:
            raise ValueError("command cannot be empty")

        if string[0] != '/':
            raise ValueError("command must begin with '/'")

        string = string[1:]
        what_remains = string.split(' ', maxsplit=1)
        command_str = what_remains[0]
        if command_str not in self.__commands:
            raise ValueError(f"no command '{command_str}'")

        command = self.__commands[command_str]
        if len(what_remains) == 2:
            arguments = command.parse_args(what_remains[1])
        else:
            arguments = {}

        return command.name, arguments


def parse(command: str):
    if not command:
        raise ValueError("command cannot be empty")

    if command[0] != '/':
        raise ValueError("commands must begin with '/'")

    command = command[1:]
