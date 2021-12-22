from cmdtools.ext.command import Command


class BaseCommand(Command):
    __help__ = None

    def __init__(self, name: str):
        super().__init__(name=name)

    @property
    def help(self):
        return self.__help__
