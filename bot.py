import os
import re
import random
import datetime
import logging

import hikari
import cmdtools
from cmdtools.ext.command import RunnerError

from lib import utils
from lib import meta


class FunnySnake(hikari.GatewayBot):
    def __init__(self, token: str):
        super().__init__(
            token=token,
        )

        # subscriptions
        self.subscribe(hikari.GuildMessageCreateEvent, self.on_message)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.StartingEvent, self.on_starting)

    async def on_starting(self, event: hikari.StartingEvent):
        self.start_time = datetime.datetime.utcnow()
        logging.info(f"Starting FunnyCoffee version v{meta.Version(0)}...")

    async def on_started(self, event: hikari.StartedEvent):
        loadcmdmsg = []
        for command in utils.get_commands():
            cmd = utils.load_command(command)

            if not hasattr(cmd, "PREFIX"):
                warnmsg = f"Command module exists, but no prefix defined: {command}"
                warnmsg += f"\n  Module contains {len(cmd.group.commands)} command(s)"
                warnmsg += "\nTo load the command module, please define PREFIX variable in global scope."
                logging.warning(warnmsg)
            else:
                loadcmdmsg.append(f"  - {command}")
        loadcmdmsg.append(f"{len(loadcmdmsg)} Command module(s) found:")
        logging.info("\n".join(loadcmdmsg[::-1]))

        await self.update_presence(
            status=hikari.Status.IDLE,
            idle_since=datetime.datetime.now(),
            activity=hikari.Activity(
                name="the hit game Among Us", type=hikari.ActivityType.PLAYING
            ),
        )

    async def on_message(self, event: hikari.GuildMessageCreateEvent):
        if event.is_human:
            message = event.message

            # hard coding garbage
            if re.search(r"funny\s*coffee", message.content, flags=re.IGNORECASE):
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))
            elif message.content.strip() == f"<@!{self.get_me().id}>":
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))

            if re.match(
                r"^funny\s*coffee\s*prefix\s*\??$", message.content, flags=re.IGNORECASE
            ):
                await message.respond("Ask again nicely.")
            elif re.match(
                r"^funny\s*coffee\s*\,?\s*prefix\s*\,?\s*ple?a?se?.?$",
                message.content,
                flags=re.IGNORECASE,
            ):
                gcom = utils.load_command("general")

                if hasattr(gcom, "PREFIX"):
                    await message.respond(
                        f"my prefix is **{gcom.PREFIX}**, try **{gcom}help**"
                    )
                else:
                    await message.respond("No.")
            else:
                for command in utils.get_commands():
                    cmdobj = utils.load_command(command)

                    if cmdobj and hasattr(cmdobj, "PREFIX"):
                        cmd = cmdtools.AioCmd(message.content, prefix=cmdobj.PREFIX)

                        if cmd.name:
                            try:
                                await cmdobj.group.run(
                                    cmd, attrs={"message": message, "client": self}
                                )
                            except RunnerError:
                                guild: hikari.RESTGuild = await self.rest.fetch_guild(
                                    message.guild_id
                                )
                                warnmsg = f"User has executed an unknown command: {message.content}"
                                warnmsg += f"\n  User:\n    Username: {message.author.username}#{message.author.discriminator}\n    ID: {message.author.id}"
                                warnmsg += f"\n  User's guild:\n    ID: {guild.id}\n    Name: {guild.name}"
                                logging.warning(warnmsg)


def main():
    if ".env" in os.listdir() and os.path.isfile(".env"):
        utils.ConfigEnv(".env")

    if not os.getenv("TOKEN"):
        print("Token is required to start the bot!")
        os.environ["TOKEN"] = utils.getin(
            "Enter Discord bot token: ", "Token is required to start the bot!"
        )
    if not os.getenv("TENOR_TOKEN"):
        print("Tenor token is required!")
        os.environ["TENOR_TOKEN"] = utils.getin(
            "Enter Tenor token: ", "Token is required!"
        )

    bot = FunnySnake(os.getenv("TOKEN"))
    opts = {}

    # if meta.Version.DEV is not meta.DevType.RELEASE:
    #     opts.update({"asyncio_debug": True, "coroutine_tracking_depth": 20})

    bot.run(**opts)


if __name__ == "__main__":
    main()
