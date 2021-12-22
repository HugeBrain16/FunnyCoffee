import os
import re
import json
import random
import datetime
import logging
import asyncio
import functools
import string

import hikari
import cmdtools
import flask
import psutil
from cmdtools.ext.command import RunnerError

from lib import utils
from lib import meta
from lib import webutil


if os.name != "nt":
    import uvloop

    uvloop.install()


class FunnyCoffee(hikari.GatewayBot):
    def __init__(self, token: str):
        self.config = json.load(open("config.json", "r", encoding="UTF-8"))
        self.webapp = flask.Flask(
            "FunnyCoffee",
            static_folder="./assets",
            template_folder="./assets",
        )
        self.webapp.permanent_session_lifetime = datetime.timedelta(days=1)
        self.webapp.secret_key = "".join(
            [random.choice(string.printable.strip()) for _ in range(16)]
        )
        self.webapp.logger = logging.getLogger("hikari.bot")

        super().__init__(
            token=token,
        )

        # subscriptions
        self.subscribe(hikari.GuildMessageCreateEvent, self.on_message)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.StartingEvent, self.on_starting)

    async def update_presence_task(self):
        while self.is_alive:
            presences = []

            presences.append(
                self.update_presence(
                    status=hikari.Status.IDLE,
                    idle_since=datetime.datetime.now(),
                    activity=hikari.Activity(
                        name="the hit game Among Us", type=hikari.ActivityType.PLAYING
                    ),
                )
            )

            general_cmd = utils.load_command("general")
            presences.append(
                self.update_presence(
                    status=hikari.Status.IDLE,
                    idle_since=datetime.datetime.now(),
                    activity=hikari.Activity(
                        name=f"{general_cmd.PREFIX}help"
                        if hasattr(general_cmd, "PREFIX")
                        else "your mom",
                        type=hikari.ActivityType.WATCHING,
                    ),
                )
            )
            for presence in presences:
                await presence
                await asyncio.sleep(60 * 5)

    async def on_starting(self, event: hikari.StartingEvent):
        logging.info(f"Starting FunnyCoffee version v{meta.Version(0)}...")

    async def on_started(self, event: hikari.StartedEvent):
        self.loop = asyncio.get_event_loop()
        self.start_time = datetime.datetime.utcnow()
        self.commands = []
        loadcmdmsg = []
        for command in utils.get_commands():
            cmd = utils.load_command(command)

            if not hasattr(cmd, "PREFIX"):
                warnmsg = f"Command module exists, but no prefix defined: {command}"
                warnmsg += f"\n  Module contains {len(cmd.group.commands)} command(s)"
                warnmsg += "\nTo load the command module, please define PREFIX variable in global scope."
                logging.warning(warnmsg)
            else:
                self.commands.append(cmd)
                loadcmdmsg.append(f"  - {command}")
        loadcmdmsg.append(f"{len(loadcmdmsg)} Command module(s) found:")
        logging.info("\n".join(loadcmdmsg[::-1]))

        config = {"load_dotenv": False, "use_reloader": False}
        config.update(self.config["webapp"])

        if self.config["debug"]:
            config.update({"debug": True})

        @self.webapp.route("/")
        @self.webapp.route("/index")
        def index():
            return flask.render_template(
                "index.html", avatar_url=self.get_me().avatar_url
            )

        @self.webapp.errorhandler(404)
        def page_not_found(error):
            return (
                '<html><head><style>body {background-image: url("https://c.tenor.com/UoPZv7kireAAAAAd/trollface-horror.gif"); background-repeat: repeat; background-color: #000000}</style></head><body></body></html>',
                404,
            )

        @self.webapp.route("/login", methods=["GET", "POST"])
        def login():
            if flask.session.get("admin"):
                return flask.redirect(flask.url_for("dashboard"))

            if flask.request.method == "POST":
                password = flask.request.form.get("password")

                if not password:
                    return flask.render_template("login.html", empty_password=True)

                if password == self.config["web"]["admin_password"]:
                    flask.session["admin"] = True
                    flask.session.permanent = True
                    return flask.redirect(flask.url_for("dashboard"))
                else:
                    return flask.render_template("login.html", wrong_password=True)

            return flask.render_template("login.html")

        @self.webapp.route("/dashboard", methods=["GET", "POST"])
        def dashboard():
            config_updated = False

            if not flask.session.get("admin"):
                return flask.redirect(flask.url_for("login"))

            if flask.request.method == "POST":
                if flask.request.form.get("adminPassword"):
                    self.config["web"]["admin_password"] = flask.request.form.get(
                        "adminPassword"
                    )

                for logconfkey in self.config["logging"]:
                    if logconfkey in flask.request.form:
                        self.config["logging"][logconfkey] = True
                    else:
                        self.config["logging"][logconfkey] = False

                if "writeToFile" in flask.request.form:
                    with open("config.json", "w") as file:
                        file.write(utils.pjson(self.config))

                for command_index, command in enumerate(self.commands):
                    category_name = command.__name__.split(".", 1)[-1]
                    prefix_input_element = category_name + "_prefix"
                    self.commands[command_index].PREFIX = (
                        flask.request.form[prefix_input_element].strip()
                        or command.PREFIX
                    )
                    for cmd_index, cmd in enumerate(command.group.commands):
                        current_command = self.commands[command_index]
                        cmd_help_input_element = cmd.name + "_help"
                        helptext = flask.request.form[cmd_help_input_element]

                        setattr(
                            current_command.group.commands[cmd_index],
                            "__help__",
                            helptext.strip(),
                        )

                config_updated = True

            return flask.render_template(
                "dashboard.html",
                avatar_url=self.get_me().avatar_url,
                admin_password=self.config["web"]["admin_password"],
                loggingConfig=self.config["logging"],
                configUpdated=config_updated,
                commands=self.commands,
            )

        @self.webapp.route("/api")
        def api_index():
            urls = {"commands": "/api/commands", "host_machine": "/api/host_machine"}

            return webutil.jsonify(urls)

        @self.webapp.route("/api/host_machine")
        def api_host_machine():
            proc = psutil.Process(os.getpid())
            mem = proc.memory_info()
            data = {
                "memory": {
                    "used": mem.vms // (1024 ** 2),
                },
                "cpu": {
                    "percent": proc.cpu_percent(0.1),
                },
            }

            return webutil.jsonify(data)

        @self.webapp.route("/api/commands")
        def api_commands():
            commands = {
                "category_count": len(self.commands),
                "command_count": sum(
                    [len(command.group.commands) for command in self.commands]
                ),
            }
            commands.update({"categories": []})
            for command in self.commands:
                cmddat = {}
                cmddat.update({"category": command.__name__.rsplit(".", 1)[-1]})
                cmddat.update({"command_count": len(command.group.commands)})
                cmddat.update({"prefix": getattr(command, "PREFIX", None)})
                cmddat.update({"commands": []})
                for cmd in command.group.commands:
                    cmdobj = {}
                    cmdobj.update({"name": cmd.name})
                    cmdobj.update({"aliases": cmd.aliases})
                    cmdobj.update({"help": getattr(cmd, "help", None)})
                    cmddat["commands"].append(cmdobj)
                commands["categories"].append(cmddat)

            return webutil.jsonify(commands)

        run_webapp = functools.partial(self.webapp.run, **config)
        self.loop.run_in_executor(None, run_webapp)

        self.loop.create_task(self.update_presence_task())

    async def on_message(self, event: hikari.GuildMessageCreateEvent):
        if event.is_human:
            message = event.message

            if re.search(r"funny\s*coffee", message.content, flags=re.IGNORECASE):
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))
            elif message.content.strip() == f"<@!{self.get_me().id}>":
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))
            else:
                for cmd in self.commands:
                    cmdobj = cmdtools.AioCmd(message.content, prefix=cmd.PREFIX)

                    if cmdobj.name:
                        try:
                            await cmd.group.run(
                                cmdobj, attrs={"message": message, "client": self}
                            )
                        except RunnerError:
                            if self.config["logging"]["unknownCommand"]:
                                guild: hikari.RESTGuild = await self.rest.fetch_guild(
                                    message.guild_id
                                )
                                warnmsg = f"User has executed an unknown command: {message.content}"
                                warnmsg += f"\n  User:\n    Username: {message.author.username}#{message.author.discriminator}\n    ID: {message.author.id}"
                                warnmsg += f"\n  User's guild:\n    ID: {guild.id}\n    Name: {guild.name}"
                                logging.warning(warnmsg)
                        else:
                            if self.config["logging"]["executedCommand"]:
                                guild: hikari.RESTGuild = await self.rest.fetch_guild(
                                    message.guild_id
                                )
                                logmsg = (
                                    f"User has executed a command: {message.content}"
                                )
                                logmsg += f"\n  User:\n    Username: {message.author.username}#{message.author.discriminator}\n"
                                logmsg += f"\n  User's guild:\n    ID: {guild.id}\n    Name: {guild.name}"
                                logging.info(logmsg)


def main():
    if ".env" in os.listdir() and os.path.isfile(".env"):
        utils.ConfigEnv(".env")

    if not os.getenv("TOKEN"):
        print("Token is required to start the bot!")
        os.environ["TOKEN"] = utils.getin(
            "Enter Discord bot token: ", "Token is required to start the bot!"
        )

    bot = FunnyCoffee(os.getenv("TOKEN"))
    opts = {}

    if bot.config["debug"]:
        opts.update({"asyncio_debug": True, "coroutine_tracking_depth": 20})

    bot.run(**opts)


if __name__ == "__main__":
    main()
