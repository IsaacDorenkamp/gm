import pytest

import commands


def test_remainder_arg_usage():
    arg = commands.RemainderArg("remainder")
    assert arg.usage == "remainder(str)..."


def test_remainder_arg_consumes_all():
    arg = commands.RemainderArg("remainder")
    value, remainder = arg.read("the remainder")
    assert value == "the remainder"
    assert remainder == ""


def test_string_arg_usage():
    arg = commands.StringArg("string")
    assert arg.usage == "string(str)"


def test_string_arg_parse():
    arg = commands.StringArg("string")
    value, remainder = arg.read("first second third")
    assert value == "first"
    assert remainder == " second third"
    value, remainder = arg.read("\"first second\" third")
    assert value == "first second"
    assert remainder == " third"
    value, remainder = arg.read("'first second' third")
    assert value == "first second"
    assert remainder == " third"
    value, remainder = arg.read("first")
    assert value == "first"
    assert remainder == ""


def test_choice_arg_usage():
    arg = commands.ChoiceArg("choice", choices=["first", "second", "third"])
    assert arg.usage == "choice(first|second|third)"


def test_choice_arg_parse():
    arg = commands.ChoiceArg("choice", choices=["a", "b", "c"])
    value, remainder = arg.read("a second third")
    assert value == "a"
    assert remainder == " second third"
    with pytest.raises(ValueError, match="'choice' must be one of: a, b, c"):
        arg.read("first second third")


def test_int_arg_usage():
    arg = commands.IntArg("int")
    assert arg.usage == "int(int)"


def test_int_arg_parse():
    arg = commands.IntArg("int")
    value, remainder = arg.read("10 remainder")
    assert value == 10
    assert remainder == " remainder"
    with pytest.raises(ValueError):
        arg.read("invalid")


def test_int_arg_parse_binary():
    arg = commands.IntArg("int", base=2)
    value, remainder = arg.read("10")
    assert value == 2
    assert remainder == ""
    with pytest.raises(ValueError):
        arg.read("3")


def test_int_arg_parse_hex():
    arg = commands.IntArg("int", base=16)
    value, remainder = arg.read("ff")
    assert value == 255
    assert remainder == ""
    value, remainder = arg.read("10")
    assert value == 16
    assert remainder == ""


def test_int_arg_parse_min_max():
    arg = commands.IntArg("int", min=1, max=10)
    with pytest.raises(ValueError, match="int must not be less than 1"):
        arg.read("0")

    with pytest.raises(ValueError, match="int must not be more than 10"):
        arg.read("11")

    value, remainder = arg.read("5")
    assert value == 5
    assert remainder == ""


def test_command_usage():
    cmd = commands.Command("cmd")
    cmd.add_argument(commands.ArgType.String, "string")
    cmd.add_argument(commands.ArgType.Int, "int")
    assert cmd.usage == "cmd string(str) int(int)"


def test_command_parse_args():
    cmd = commands.Command("cmd")
    cmd.add_argument(commands.ArgType.String, "string")
    cmd.add_argument(commands.ArgType.Int, "int")

    args, remainder = cmd.parse_args("string 10 remainder")
    assert args == { "string": "string", "int": 10 }
    assert remainder == " remainder"

    with pytest.raises(ValueError, match="missing argument 'int'"):
        cmd.parse_args("string")

    args, remainder = cmd.parse_args("string      23")
    assert args == { "string": "string", "int": 23 }
    assert remainder == ""


def test_command_parser_parse_command():
    parser = commands.CommandParser()

    add_cmd = commands.Command("add")
    add_cmd.add_argument(commands.ArgType.String, "character")
    add_cmd.add_argument(commands.ArgType.Int, "count")

    rm_cmd = commands.Command("rm")
    rm_cmd.add_argument(commands.ArgType.String, "character")

    parser.add_command(add_cmd)
    parser.add_command(rm_cmd)

    name, args = parser.parse_command("/add character 10")
    assert name == "add"
    assert args == { "character": "character", "count": 10 }

    with pytest.raises(commands.CommandParseError, match="missing argument 'count'"):
        parser.parse_command("/add character")

    with pytest.raises(commands.CommandParseError, match="no command 'cmd'"):
        parser.parse_command("/cmd")

    with pytest.raises(commands.CommandParseError, match="command must begin with '/'"):
        parser.parse_command("add")

    with pytest.raises(commands.CommandParseError, match="command cannot be empty"):
        parser.parse_command("")

    with pytest.raises(commands.CommandParseError, match="received more arguments than expected"):
        parser.parse_command("/rm character 10")

