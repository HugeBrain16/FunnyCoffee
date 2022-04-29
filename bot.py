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
import lavasnek_rs
import pymongo
import dns.resolver

from lib import utils
from lib import meta
from lib import webutil
from lib import cache
from lib import command as libcommand


if os.name != "nt":
    try:
        import uvloop

        print("uvloop found!, installing uvloop...")
        uvloop.install()
    except ImportError:
        pass


class LavalinkEventHandler:
    def __init__(self, client: hikari.GatewayBot):
        self.client = client

    async def track_start(
        self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackStart
    ):
        node = await lavalink.get_guild_node(event.guild_id)

        if node:
            if node.now_playing:
                track = node.now_playing.track

                embed = hikari.Embed()
                embed.color = 0xFFFFFF
                embed.url = track.info.uri
                embed.title = track.info.title

                embed.set_author(name="Now playing...")
                if utils.get_youtube_thumb(track.info.uri):
                    embed.set_thumbnail(utils.get_youtube_thumb(track.info.uri))
                if node.now_playing.requester:
                    member = await self.client.rest.fetch_member(
                        event.guild_id, node.now_playing.requester
                    )

                    if member:
                        embed.set_footer(
                            text=f"Requested by {member.nickname or member.username}"
                        )

                node_data = node.get_data()

                if isinstance(node_data, dict):
                    await self.client.rest.create_message(
                        node_data["request_channel_id"], embed=embed
                    )

    async def track_finish(
        self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackFinish
    ):
        logging.info(f"Track finished on guild: {event.guild_id}")

    async def track_exception(
        self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackException
    ):
        logging.warning(f"Track caught an exception on guild: {event.guild_id}")

        skip = await lavalink.skip(event.guild_id)
        node = await lavalink.get_guild_node(event.guild_id)

        if not node:
            return

        if skip:
            if not node.queue and not node.now_playing:
                await lavalink.stop(event.guild_id)


class FunnyCoffee(hikari.GatewayBot):
    def __init__(self, token: str):
        self._config_fallback = utils.load_config()
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
        self.lavalink = lavasnek_rs.Lavalink
        self.caches = cache.MemCacheManager()
        self.mongo_client = None

        super().__init__(
            token=token,
        )

        # subscriptions
        self.subscribe(hikari.GuildMessageCreateEvent, self.on_message)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.StartingEvent, self.on_starting)
        self.subscribe(hikari.ShardReadyEvent, self.on_ready)

    @property
    def config(self):
        try:
            self._config_fallback = utils.load_config()
            return self._config_fallback
        except json.decoder.JSONDecodeError:
            return self._config_fallback

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

    async def on_ready(self, event: hikari.ShardReadyEvent):
        lavalbuilder = lavasnek_rs.LavalinkBuilder(event.my_user.id, os.getenv("TOKEN"))
        lavalbuilder = lavalbuilder.set_host(
            os.getenv("LAVALINK_HOSTNAME", "127.0.0.1")
        )
        lavalport = 2333
        _lavalport = os.getenv("LAVALINK_PORT", lavalport)

        if isinstance(_lavalport, str):
            if _lavalport.strip().isdigit():
                lavalport = int(_lavalport)
            else:
                logging.warn(
                    f"Environment 'LAVALINK_PORT' with value of '{_lavalport}' is not a digit string, falling back to default value: {lavalport}"
                )

        lavalbuilder = lavalbuilder.set_port(lavalport)
        if os.getenv("LAVALINK_PASSWORD"):
            lavalbuilder = lavalbuilder.set_password(os.getenv("LAVALINK_PASSWORD"))

        lavaclient = await lavalbuilder.build(LavalinkEventHandler(self))
        self.lavalink = lavaclient

        if os.getenv("MONGO_SRV"):
            db_con_retry = 0
            update_nameservers = False

            logging.info("Connecting to mongodb database...")
            while self.mongo_client is None and db_con_retry < 3:
                try:
                    client = pymongo.MongoClient(os.getenv("MONGO_SRV"))
                except pymongo.errors.ConfigurationError:
                    db_con_retry += 1
                    logging.error(
                        f"Couldn't connect to mongodb database, retrying... [{3 - db_con_retry} attempt(s) left]"
                    )
                    if update_nameservers is False:
                        logging.info("Updating default dns resolver's nameservers...")
                        dns.resolver.default_resolver = dns.resolver.Resolver(
                            configure=False
                        )
                        dns.resolver.default_resolver.nameservers = [
                            "9.9.9.9",  # quad9
                            "1.1.1.1",  # cloudflare
                            "8.8.8.8",  # google
                            "208.67.222.222",  # opendns
                        ]
                        update_nameservers = True
                else:
                    self.mongo_client = client
            else:
                if self.mongo_client is None:
                    logging.warning(
                        "Couldn't connect to mongodb database, some features may be unavailable."
                    )
                else:
                    logging.info("Connected to mongodb database!")

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
                        cmd_aliases_input_element = cmd.name + "_aliases"
                        cmd_disabled = cmd.name + "_disabled"
                        helptext = flask.request.form[cmd_help_input_element]
                        aliases = [
                            alias.strip()
                            for alias in flask.request.form[
                                cmd_aliases_input_element
                            ].split(",")
                        ]

                        setattr(
                            current_command.group.commands[cmd_index],
                            "__help__",
                            helptext.strip(),
                        )
                        setattr(
                            current_command.group.commands[cmd_index],
                            "__aliases__",
                            aliases,
                        )

                        if cmd_disabled in flask.request.form:
                            cmd.__disabled__ = True
                        else:
                            cmd.__disabled__ = False

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
                    "used": mem.vms // (1024**2),
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
        self.loop.create_task(self.caches.update())
        self.loop.create_task(cache.update_cachedir(".cache"))
        self.loop.create_task(libcommand.update_cooldown(self.commands))

    async def on_message(self, event: hikari.GuildMessageCreateEvent):
        if event.is_human:
            message = event.message

            if re.search(r"funny\s*coffee", message.content, flags=re.IGNORECASE):
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))
            elif message.content.strip() == f"<@!{self.get_me().id}>":
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))
            else:
                for cmd in self.commands:
                    cmdobj = cmdtools.Cmd(message.content, prefix=cmd.PREFIX)

                    if cmdobj.name:
                        try:
                            await cmd.group.run(
                                cmdobj, attrs={"message": message, "client": self}
                            )
                        except cmdtools.NotFoundError:
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
