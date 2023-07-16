import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

import cmdtools
from cmdtools.callback import Callback
from cmdtools.ext.command import Command, Group

from lib import utils


class BaseCommand(Command):
    __help__ = None
    __disabled__ = False

    def __init__(self, name: str):
        self._cooldown = 0
        self._cooldowns = {}
        self._cooldown_callback: Optional[Callback] = None
        super().__init__(name=name)

    def _cooldown_gettr(self, id):
        return utils.ftime((self._cooldowns[id] - datetime.now()).seconds)

    @property
    def help(self):
        return self.__help__


class BaseGroup(Group):
    async def run(self, command, *, attrs=None):
        for cmd in self.commands:
            if cmd.name == command.name or command.name in cmd.aliases:
                if not cmd.__disabled__:
                    author_id = attrs["message"].author.id
                    if author_id not in cmd._cooldowns:
                        cmd._cooldowns.update({author_id: datetime.now()})
                    for userid in cmd._cooldowns:
                        usercd = cmd._cooldowns[userid]

                        if usercd < datetime.now():
                            if cmd._cooldown > 0:
                                cmd._cooldowns[userid] = datetime.now() + timedelta(
                                    seconds=cmd._cooldown
                                )
                            return await super().run(command, attrs=attrs)
                        else:
                            if isinstance(cmd._cooldown_callback, Callback):
                                await cmdtools.execute(
                                    command, cmd._cooldown_callback, attrs=attrs
                                )
