import os
import importlib
from cmdtools.ext.command import CommandWrapper
from typing import List


class ConfigEnv:
    def __init__(self, filepath: str):
        self.filepath = filepath

        cfg = open(filepath, "r").readlines()

        for line in cfg:
            line = line.strip()

            if line:
                key, value = self.parse_option(line)

                if key and value:
                    os.environ[key] = value

    def parse_option(self, string: str):
        key = None
        value = None

        token = string.split("=", 1)

        if len(token) == 2:
            key = token[0].strip()
            value = token[1].strip()

        return key, value


def load_command(name: str):
    """load commands from library"""
    for file in os.listdir("commands"):
        if file.endswith(".py") and os.path.isfile("commands/" + file):
            modname = file.rsplit(".py", 1)[0]
            modpath = os.path.join("commands", modname).replace(os.sep, ".")
            mod = importlib.import_module(modpath)

            if hasattr(mod, "group") and name == modname:
                return mod if isinstance(mod.group, CommandWrapper) else None


def get_commands() -> List[str]:
    """get command names from library"""
    cmds = []

    for file in os.listdir("commands"):
        if file.endswith(".py") and os.path.isfile("commands/" + file):
            modname = file.rsplit(".py", 1)[0]
            mod = load_command(modname)

            if mod:
                cmds.append(modname)

    return cmds


def mention_to_id(mention: str) -> int:
    """extract user id from discord mention"""
    result = 0

    try:
        result = int(
            mention.replace("<", "").replace(">", "").replace("!", "").replace("@", "")
        )
    except (AttributeError, ValueError):
        pass

    return result


def getin(prompt: str, empty_message: str = None):
    res = input(prompt)

    while not res:
        if isinstance(empty_message, str):
            print(empty_message)
        res = input(prompt)

    return res
