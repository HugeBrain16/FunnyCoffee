import importlib
import importlib.util
import inspect
import json
import os
from glob import glob
from typing import Iterable, List
from urllib import parse as urlparse

from cmdtools.ext.command import Group


class ConfigEnv:
    def __init__(self, filepath: str, comment_prefix: Iterable[str] = ("#", ";")):
        self.filepath = filepath
        self.comment_prefix = comment_prefix

        cfg = open(filepath, "r").readlines()

        for line in cfg:
            line = line.strip()

            if line and not line.startswith(self.comment_prefix):
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
    files = glob(os.path.join("commands", f"{name}.py"))

    if not files:
        return None

    # Use the importlib.util.find_spec function to get the module
    # specification for the specified module.
    spec = importlib.util.find_spec(f"commands.{name}")

    if not spec.loader:
        return None

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if hasattr(mod, "group") and issubclass(getattr(mod, "group").__class__, Group):
        return mod

    return None


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


def pjson(data: dict):
    return json.dumps(
        data,
        indent=4,
        sort_keys=4,
        separators=(",", ": "),
    )


def get_youtube_thumb(url: str):
    query = urlparse.parse_qs(urlparse.urlsplit(url).query)

    if query.get("v"):
        return f"http://i3.ytimg.com/vi/{query.get('v')[0]}/hqdefault.jpg"


def load_config():
    return json.load(open("config.json", "r", encoding="UTF-8"))
