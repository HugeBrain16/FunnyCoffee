import asyncio
import datetime
import functools
import json
import logging
import os
import random
import re
import string

import cmdtools
import dns.resolver
import flask
import hikari
import lavalink
import psutil
import pymongo

from lib import cache
from lib import command as libcommand
from lib import meta, utils, webutil

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

    @lavalink.listener(lavalink.TrackStartEvent)  # type: ignore
    async def track_start(self, event: lavalink.TrackStartEvent):
        embed = hikari.Embed()
        embed.color = 0xFFFFFF
        embed.url = event.track.uri
        embed.title = event.track.title

        embed.set_author(name="Now playing...")
        if utils.get_youtube_thumb(event.track.uri):
            embed.set_thumbnail(utils.get_youtube_thumb(event.track.uri))

        member = await self.client.rest.fetch_member(
            event.player.guild_id, event.track.requester
        )

        if member:
            embed.set_footer(text=f"Requested by {member.nickname or member.username}")

        await self.client.rest.create_message(
            event.track.extra["request_channel_id"], embed=embed
        )

    @lavalink.listener(lavalink.TrackEndEvent)  # type: ignore
    async def track_finish(self, event: lavalink.TrackEndEvent):
        logging.info(f"Track finished on guild: {event.player.guild_id}")

    @lavalink.listener(lavalink.TrackExceptionEvent)  # type: ignore
    async def track_exception(self, event: lavalink.TrackExceptionEvent):
        logging.warning(f"Track caught an exception on guild: {event.player.guild_id}")

        player = self.client.lavalink.player_manager.get(event.player.guild_id)

        if isinstance(player, lavalink.DefaultPlayer):
            if not player.is_playing and not player.queue:
                await player.stop()
            else:
                await player.skip()

    @lavalink.listener(lavalink.QueueEndEvent)  # type: ignore
    async def queue_finish(self, event: lavalink.QueueEndEvent):
        logging.info(f"Queue finished on guild: {event.player.guild_id}")


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
        self.lavalink = lavalink.Client
        self.caches = cache.MemCacheManager()
        self.mongo_client = None

        super().__init__(
            intents=hikari.Intents.ALL,
            token=token,
        )

        # subscriptions
        self.subscribe(hikari.GuildMessageCreateEvent, self.on_message)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.StartingEvent, self.on_starting)
        self.subscribe(hikari.ShardReadyEvent, self.on_ready)
        self.subscribe(hikari.StoppingEvent, self.on_stopping)
        self.subscribe(hikari.VoiceServerUpdateEvent, self.voice_server_update)
        self.subscribe(hikari.VoiceStateUpdateEvent, self.voice_state_update)

    @property
    def config(self):
        try:
            self._config_fallback = utils.load_config()
            return self._config_fallback
        except json.decoder.JSONDecodeError:
            return self._config_fallback

    async def voice_server_update(self, event: hikari.VoiceServerUpdateEvent):
        data = {
            "t": "VOICE_SERVER_UPDATE",
            "d": {
                "guild_id": event.guild_id,
                "endpoint": event.endpoint[6:],  # get rid of wss://
                "token": event.token,
            },
        }

        await self.lavalink.voice_update_handler(data)

    async def voice_state_update(self, event: hikari.VoiceStateUpdateEvent):
        data = {
            "t": "VOICE_STATE_UPDATE",
            "d": {
                "guild_id": event.state.guild_id,
                "user_id": event.state.user_id,
                "channel_id": event.state.channel_id,
                "session_id": event.state.session_id,
            },
        }

        await self.lavalink.voice_update_handler(data)

    async def on_ready(self, event: hikari.ShardReadyEvent):
        lvport = 2333
        _lvport = os.getenv("LAVALINK_PORT", lvport)

        if isinstance(_lvport, str):
            if _lvport.strip().isdigit():
                lvport = int(_lvport)
            else:
                logging.warn(
                    f"Environment 'LAVALINK_PORT' with value of '{_lvport}' is not a digit string, falling back to default value: {lvport}"
                )

        lvclient = lavalink.Client(event.my_user.id)
        lvclient.add_node(
            host=os.getenv("LAVALINK_HOSTNAME", "127.0.0.1"),
            port=lvport,
            password=os.getenv("LAVALINK_PASSWORD", "youshallnotpass"),
            region="us",
        )

        lvclient.add_event_hooks(LavalinkEventHandler(self))
        self.lavalink = lvclient

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

    async def on_stopping(self, event: hikari.StoppingEvent):
        if self.mongo_client:
            self.mongo_client.close()

    async def on_started(self, event: hikari.StartedEvent):
        self.loop = asyncio.get_event_loop()
        self.start_time = datetime.datetime.utcnow()
        self.commands = []
        loadcmdmsg = []
        for command in utils.get_commands():
            cmd = utils.load_command(command)

            if not hasattr(cmd, "PREFIX"):
                warnmsg = f"The command module has been found, but no prefix is defined: {command}"
                warnmsg += (
                    f"\n  The module contains {len(cmd.group.commands)} command(s)"
                )
                warnmsg += "\nTo load the command module, define the PREFIX variable in the global scope."
                logging.warning(warnmsg)
            else:
                self.commands.append(cmd)
                loadcmdmsg.append(f"  - {command}")
        loadcmdmsg.append(f"loaded {len(loadcmdmsg)} Command module(s):")
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
                    "used": mem.rss // (1024**2),
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

        self.loop.create_task(self.caches.update())
        self.loop.create_task(cache.update_cachedir(".cache"))
        self.loop.create_task(libcommand.update_cooldown(self.commands))

        general_cmd = utils.load_command("general")
        await self.update_presence(
            status=hikari.Status.IDLE,
            idle_since=datetime.datetime.now(),
            activity=hikari.Activity(
                name=f"{general_cmd.PREFIX}help"
                if hasattr(general_cmd, "PREFIX")
                else None,
                type=hikari.ActivityType.WATCHING,
            ),
        )

    async def on_message(self, event: hikari.GuildMessageCreateEvent):
        if event.is_human:
            message = event.message

            if re.search(
                rf"^(funny\s*coffee|<@{self.get_me().id}>)$",
                message.content,
                flags=re.IGNORECASE,
            ):
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
