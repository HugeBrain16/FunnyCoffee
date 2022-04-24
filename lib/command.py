from cmdtools.ext.command import Command, Group


class BaseCommand(Command):
    __help__ = None
    __disabled__ = False

    def __init__(self, name: str):
        super().__init__(name=name)

    @property
    def help(self):
        return self.__help__


class BaseGroup(Group):
    async def run(self, command, *, attrs = None):
        for cmd in self.commands:
            if cmd.name == command.name or command.name in cmd.aliases:
                if not cmd.__disabled__:
                    return await super().run(command, attrs=attrs)
