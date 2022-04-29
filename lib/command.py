import asyncio
import cmdtools
from cmdtools.ext.command import Command, Group
from cmdtools.callback import Callback
from typing import List, Optional, Dict


class Cooldown:
    def __init__(self, interval: int = 0):
        self.set_interval(interval)

    def set_interval(self, interval: int):
        self.interval = 0 if interval <= 0 else interval


class BaseCommand(Command):
    __help__ = None
    __disabled__ = False

    def __init__(self, name: str):
        self._cooldown = Cooldown()
        self._user_cooldown = {}
        self._cooldown_callback: Optional[Callback] = None
        super().__init__(name=name)

    @property
    def help(self):
        return self.__help__


class BaseGroup(Group):
    async def run(self, command, *, attrs=None):
        for cmd in self.commands:
            if cmd.name == command.name or command.name in cmd.aliases:
                if not cmd.__disabled__:
                    author_id = attrs["message"].author.id
                    if author_id not in cmd._user_cooldown:
                        cmd._user_cooldown.update({author_id: 0})
                    for userid in cmd._user_cooldown:
                        usercd = cmd._user_cooldown[userid]

                        if usercd == 0:
                            if cmd._cooldown.interval > 0:
                                cmd._user_cooldown[userid] = cmd._cooldown.interval
                            return await super().run(command, attrs=attrs)
                        else:
                            if isinstance(cmd._cooldown_callback, Callback):
                                await cmdtools.execute(
                                    command, cmd._cooldown_callback, attrs=attrs
                                )


async def update_cooldown(commands: List[BaseGroup]):
    while True:
        for cmdmod in commands:
            for cmd in cmdmod.group.commands:
                if cmd._cooldown.interval > 0:
                    for userid in cmd._user_cooldown:
                        if cmd._user_cooldown[userid] > 0:
                            cmd._user_cooldown[userid] -= 1
        await asyncio.sleep(1.0)
