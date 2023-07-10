import importlib
import importlib.util
import json
import os
import re
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
    return [
        file.rsplit(os.sep, 1)[1].rsplit(".py", 1)[0]
        for file in glob(os.path.join("commands", "*.py"))
    ]


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


def get_mentions_ids(msg):
    return re.findall("<@(?P<user>\d+)>|<#(?P<channel>\d+)>", msg)


def fsec(x):
    if (x / 60) < 1:
        return f"{x} second" + "s" if x > 1 else ""
    elif (x / 60) >= 1 and (x / 3600) < 1:
        return f"{int(x/60)} minute" + "s" if int(x / 60) > 1 else ""
    elif (x / 3600) >= 1 and (x / 86400) < 1:
        return f"{int(x/3600)} hour" + "s" if int(x / 3600) > 1 else ""
    elif (x / 86400) >= 1 and (x / 2628002.88) < 1:
        return f"{int(x/86400)} day" + "s" if int(x / 86400) > 1 else ""
    elif (x / 2628002.88) >= 1:
        return f"{int(x/2628002.88)} month" + "s" if int(x / 2628002.88) > 1 else ""
