import typing


def get_yesno(question: str, default: bool = True):
    suffix = "[Y/n] " if default else "[y/N] "
    while True:
        result = input(f"{question} {suffix}")
        if not result:
            return default
        elif result.lower() == 'y':
            return True
        elif result.lower() == 'n':
            return False
        else:
            print("Please enter Y or N.")


T = typing.TypeVar('T')


_SENTINEL = object()


def aggregate(items: typing.Iterable[T], key: typing.Callable[[T], typing.Any]) -> list[list[T]]:
    aggregated: list[list[T]] = []
    current_key = _SENTINEL
    for item in items:
        this_key = key(item)
        if current_key != this_key:
            current_key = this_key
            aggregated.append([])
        aggregated[-1].append(item)
    return aggregated

__all__ = [
    "aggregate",
    "get_yesno",
]
