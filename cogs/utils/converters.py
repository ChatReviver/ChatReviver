import re
from datetime import timedelta

from discord.ext.commands import BadArgument


def timeout_parser(arg) -> timedelta:
    if (match := re.match(r"(\d+?)\s?(s(?=$|econds?)|m(?=$|inutes?)|h(?=$|ours?)|d(?=$|ays?))", arg)) is None:
        raise BadArgument

    shorthands = {
        "s": "seconds",
        "m": "minutes",
        "h": "hours",
        "d": "days"
    }

    return timedelta(**{shorthands[match.group(2)]: int(match.group(1))})
