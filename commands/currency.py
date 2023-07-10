import random
from enum import Enum

import cmdtools
import hikari
from cmdtools.callback import Callback

from lib import command, utils

USER_DATA = {
    "balance": 0,
    "level": 0,
    "xp": 0,
    "xpmax": 50,
    "job": 0,
}


class ItemType(Enum):
    COLLECTABLE = 1


ITEMS = [
    {
        "id": "cookie",
        "name": "Cookie",
        "desc": "A food.",
        "type": ItemType.COLLECTABLE,
        "value": 30,
        "emoji": ":cookie:",
    },
    {
        "id": "diamond",
        "name": "Diamond",
        "desc": "Gemerald.",
        "type": ItemType.COLLECTABLE,
        "value": 999999,
        "emoji": ":gem:",
    },
]


class Group(command.BaseGroup):
    async def run(self, command, *, attrs=None):
        for cmd in self.commands:
            if (
                cmd.name == command.name
                or command.name in cmd.aliases
                and not cmd.__disabled__
            ):
                if attrs["client"].mongo_client is None:
                    return await attrs["message"].respond(
                        "this feature is not available"
                    )

                return await super().run(command, attrs=attrs)


group = Group("Currency")
PREFIX = "c!"


def item_exists(name):
    return name in [item["id"] for item in ITEMS]


def get_item(name):
    for item in ITEMS:
        if item["id"] == name:
            return item


def setup_user(db, userid):
    data = USER_DATA
    data.update({"userid": userid})
    data["inventory"] = {}
    for item in ITEMS:
        data["inventory"][item["id"]] = 0

    db["currency"].update_one(data, {"$set": data}, upsert=True)


@group.add_option("id")
@group.add_option("qty", default=1, type=int)
@group.command("buy")
class Buy(command.BaseCommand):
    __help__ = "buy item from item shop"

    async def error_buy(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "id":
                await ctx.attrs.message.respond("Specify the item id you want to buy")
        elif isinstance(ctx.error, cmdtools.ConversionError):
            if ctx.error.option == "qty":
                await ctx.attrs.message.respond("value must be digits!")
        else:
            raise ctx.error

    async def buy(self, ctx):
        db = ctx.attrs.client.mongo_client["funnycoffee"]
        filter = {"userid": ctx.attrs.message.author.id}
        data = db["currency"].find_one(filter)

        if data:
            msg = await ctx.attrs.message.respond("Buying item...", reply=True)

            if not item_exists(ctx.options.id):
                return await msg.edit(f"Item with id `{ctx.options.id}` does not exist")

            if ctx.options.qty < 1:
                return await msg.edit("You can buy at least 1 item")

            item = get_item(ctx.options.id)
            total_price = item["value"] * ctx.options.qty
            if data.get("balance", 0) < total_price:
                return await msg.edit("Not enough coins")

            db["currency"].update_one(filter, {"$inc": {"balance": -total_price}})
            data["inventory"][item["id"]] += ctx.options.qty
            db["currency"].update_one(filter, {"$set": data})
            await msg.edit(
                f"You bought **{item['emoji'] if item['emoji'] else ''} {item['name']} x{ctx.options.qty}**"
            )
        else:
            setup_user(db, filter["userid"])
            await self.buy(ctx)


@group.add_option("user")
@group.add_option("id")
@group.add_option("qty", default=1, type=int)
@group.command("give")
class Give(command.BaseCommand):
    __help__ = "give item to other user"

    async def error_give(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "user":
                await ctx.attrs.message.respond(
                    "You have to mention someone you want to give your items to",
                    reply=True,
                )
            elif ctx.error.option == "id":
                await ctx.attrs.message.respond("Specify the item id you want to give")
        elif isinstance(ctx.error, cmdtools.ConversionError):
            if ctx.error.option == "qty":
                await ctx.attrs.message.respond(
                    "Specify the quantity in digits!", reply=True
                )
        elif isinstance(ctx.error, hikari.NotFoundError):
            await ctx.attrs.message.respond("User not found!", reply=True)
        else:
            raise ctx.error

    async def give(self, ctx):
        db = ctx.attrs.client.mongo_client["funnycoffee"]
        filter = {"userid": ctx.attrs.message.author.id}
        data = db["currency"].find_one(filter)

        if data:
            msg = await ctx.attrs.message.respond("Giving your items...", reply=True)
            mention = utils.get_mentions_ids(ctx.options.user)

            if mention:
                user = await ctx.attrs.client.rest.fetch_member(
                    ctx.attrs.message.guild_id, mention[0][0]
                )

                if not user:
                    return await msg.edit("User not found!")

                if not item_exists(ctx.options.id):
                    return await msg.edit(
                        f"Item with id `{ctx.options.id}` does not exist"
                    )

                if ctx.options.qty < 1:
                    return await msg.edit("You can give at least 1 item")

                item = get_item(ctx.options.id)
                if data["inventory"][item["id"]] < ctx.options.qty:
                    return await msg.edit("You don't have enough items to give")

                tuser = db["currency"].find_one({"userid": user.id})

                if not tuser:
                    setup_user(db, user.id)
                    tuser = db["currency"].find_one({"userid": user.id})

                data["inventory"][item["id"]] -= ctx.options.qty
                tuser["inventory"][item["id"]] += ctx.options.qty
                db["currency"].update_one(filter, {"$set": data})
                db["currency"].update_one({"userid": user.id}, {"$set": tuser})
                await msg.edit(
                    f"You gave **{item['emoji'] if item['emoji'] else ''} {item['name']} x{ctx.options.qty}** to **{user.username}**"
                )
            else:
                return await msg.edit(
                    "You have to mention someone you want to give your items to"
                )
        else:
            setup_user(db, filter["userid"])
            await self.give(ctx)


@group.add_option("page", type=int, default=1)
@group.command("inventory", aliases=["inv"])
class Inventory(command.BaseCommand):
    __help__ = "inventory"

    async def inventory(self, ctx):
        db = ctx.attrs.client.mongo_client["funnycoffee"]
        filter = {"userid": ctx.attrs.message.author.id}
        data = db["currency"].find_one(filter)

        if data:
            msg = await ctx.attrs.message.respond("Loading inventory...", reply=True)

            pages = []
            c_page = []

            for item in ITEMS:
                if data["inventory"][item["id"]] > 0 and len(c_page) < 5:
                    c_page.append(item)
                else:
                    pages.append(c_page)
                    c_page = []

            if c_page and len(pages) < 5:
                pages.append(c_page)
                c_page = []

            if ctx.options.page < 1 or ctx.options.page > len(pages):
                return await msg.edit(f"Page {ctx.options.page} does not exist")

            if not pages:
                return await msg.edit("Nothing to show")

            embed = hikari.Embed()
            embed.title = "Inventory"
            embed.description = f"{ctx.attrs.message.author.username}'s inventory"
            embed.color = 0xFFFF00
            embed.set_footer(f"Showing page {ctx.options.page} of {len(pages)}")

            for item in pages[ctx.options.page - 1]:
                desc = f"{item['desc']}\n\n"
                desc += f"type: `{item['type'].name}`\n"
                desc += f"total value: **{item['value'] * data['inventory'][item['id']]}**\n"
                desc += f"id: `{item['id']}`\n"
                embed.add_field(
                    name=f"{item['emoji'] if item['emoji'] else ''} {item['name']} x{data['inventory'][item['id']]}",
                    value=desc,
                )

            await msg.edit(content="", embed=embed)
        else:
            setup_user(db, filter)
            await self.inventory(ctx)


@group.add_option("page", type=int, default=1)
@group.command("shop")
class Shop(command.BaseCommand):
    __help__ = "item shop"

    async def shop(self, ctx):
        msg = await ctx.attrs.message.respond("Loading item shop...")

        pages = []
        c_page = []

        for item in ITEMS:
            if item["value"] and len(c_page) < 5:
                c_page.append(item)
            else:
                pages.append(c_page)
                c_page = []

        if c_page and len(pages) < 5:
            pages.append(c_page)
            c_page = []

        if ctx.options.page < 1 or ctx.options.page > len(pages):
            return await msg.edit(f"Page {ctx.options.page} does not exist")

        embed = hikari.Embed()
        embed.title = "Shop"
        embed.description = "item shop"
        embed.color = 0xFFFF00
        embed.set_footer(f"Showing page {ctx.options.page} of {len(pages)}")

        for item in pages[ctx.options.page - 1]:
            desc = f"{item['desc']}\n\n"
            desc += f"type: `{item['type'].name}`\n"
            desc += f"price: **{item['value']}**\n"
            desc += f"id: `{item['id']}`\n"
            embed.add_field(
                name=f"{item['emoji']} {item['name']}"
                if item["emoji"]
                else item["name"],
                value=desc,
            )

        await msg.edit(content="", embed=embed)


@group.command("balance", aliases=["bal"])
class Balance(command.BaseCommand):
    __help__ = "show your balance"

    async def balance(self, ctx):
        db = ctx.attrs.client.mongo_client["funnycoffee"]
        filter = {"userid": ctx.attrs.message.author.id}
        data = db["currency"].find_one(filter)

        if data:
            embed = hikari.Embed()
            embed.title = f"{ctx.attrs.message.author.username}'s balance"
            embed.description = f":coin: **{data.get('balance', 0)}** coins."
            embed.color = 0xFFFF00

            await ctx.attrs.message.respond(embed=embed, reply=True)
        else:
            setup_user(db, filter["userid"])
            await self.balance(ctx)


@group.add_option("bet", type=int, default=0)
@group.command("dice")
class Dice(command.BaseCommand):
    __help__ = "dice gambling"

    async def error_dice(self, ctx):
        if isinstance(ctx.error, cmdtools.ConversionError):
            return await ctx.attrs.message.respond("bet must be digits!", reply=True)
        else:
            raise ctx.error

    async def dice(self, ctx):
        db = ctx.attrs.client.mongo_client["funnycoffee"]
        filter = {"userid": ctx.attrs.message.author.id}
        data = db["currency"].find_one(filter)

        if data:
            if ctx.options.bet < 1:
                return await ctx.attrs.message.respond(
                    "You must place a bet at least 1 coin"
                )

            if data.get("balance", 0) < ctx.options.bet:
                return await ctx.attrs.message.respond("You don't have enough coins")

            msg = await ctx.attrs.message.respond("Rolling dice...", reply=True)
            ud = random.randint(1, 6) + random.randint(1, 6)
            bd = random.randint(1, 6) + random.randint(1, 6)
            embed = hikari.Embed()
            embed.title = ":game_die: Dice"
            if ud == bd:
                embed.description = "Draw!"
                embed.color = 0xFFFFFF
            elif ud > bd:
                embed.description = "You Win!"
                embed.color = 0x00FF00
                db["currency"].update_one(
                    filter, {"$inc": {"balance": ctx.options.bet}}
                )
            else:
                embed.description = "You Lose!"
                embed.color = 0xFF0000
                db["currency"].update_one(
                    filter, {"$inc": {"balance": -ctx.options.bet}}
                )
            embed.add_field(
                name="You", value=f"**{ud}**" if ud > bd else f"{ud}", inline=True
            )
            embed.add_field(
                name="Bot", value=f"**{bd}**" if bd > ud else f"{bd}", inline=True
            )
            await msg.edit(content="", embed=embed)
        else:
            setup_user(db, filter["userid"])
            await self.dice(ctx)


@group.command("beg")
class Beg(command.BaseCommand):
    __help__ = "beg for coins"

    def __init__(self):
        super().__init__(name="beg")
        self._cooldown = 30
        self._cooldown_callback = Callback(self.cd_beg)

    async def cd_beg(self, ctx):
        await ctx.attrs.message.respond(
            f"You can do this again in {(self._cooldown_gettr(ctx.attrs.message.author.id))}",
            reply=True,
        )

    async def beg(self, ctx):
        db = ctx.attrs.client.mongo_client["funnycoffee"]
        filter = {"userid": ctx.attrs.message.author.id}
        data = db["currency"].find_one(filter)

        if data:
            msg = await ctx.attrs.message.respond("Begging...")
            lootget = random.randint(1, 5)

            embed = hikari.Embed()
            embed.title = "Beg"
            embed.color = 0x00FF00
            if lootget != 3:
                gem = random.randint(5, 30)
                embed.description = f"Someone gave you :coin: **{gem}** coins"
                db["currency"].update_one(filter, {"$inc": {"balance": gem}})
            else:
                embed.description = f"Someone gave you a **:cookie: Cookie**"
                data["inventory"]["cookie"] += 1
                db["currency"].update_one(filter, {"$set": data})
            await msg.edit(content="", embed=embed)
        else:
            setup_user(db, filter["userid"])
            await self.beg(ctx)


@group.add_option("user")
@group.add_option("coin", default=0, type=int)
@group.command("givecoin")
class GiveCoin(command.BaseCommand):
    __help__ = "Give your coins to other user"

    async def error_givecoin(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "user":
                await ctx.attrs.message.respond(
                    "You have to mention someone you want to give your coins to",
                    reply=True,
                )
            elif ctx.error.option == "coin":
                await ctx.attrs.message.respond(
                    "Specify the amount of coins you want to give"
                )
        elif isinstance(ctx.error, cmdtools.ConversionError):
            if ctx.error.option == "coin":
                await ctx.attrs.message.respond("`coin` must be digits!", reply=True)
        elif isinstance(ctx.error, hikari.NotFoundError):
            await ctx.attrs.message.respond("User not found!", reply=True)
        else:
            raise ctx.error

    async def givecoin(self, ctx):
        db = ctx.attrs.client.mongo_client["funnycoffee"]
        filter = {"userid": ctx.attrs.message.author.id}
        data = db["currency"].find_one(filter)

        if data:
            msg = await ctx.attrs.message.respond("Giving your coins...", reply=True)
            mention = utils.get_mentions_ids(ctx.options.user)

            if mention:
                user = await ctx.attrs.client.rest.fetch_member(
                    ctx.attrs.message.guild_id, mention[0][0]
                )

                if not user:
                    return await msg.edit("User not found!")

                if ctx.options.coin < 1:
                    return await msg.edit("You can give at least 1 coin")

                if data.get("balance", 0) < ctx.options.coin:
                    return await msg.edit("You don't have enough coins")

                tuser = db["currency"].find_one({"userid": user.id})

                if not tuser:
                    setup_user(db, user.id)

                db["currency"].update_one(
                    filter, {"$inc": {"balance": -ctx.options.coin}}
                )
                db["currency"].update_one(
                    {"userid": user.id}, {"$inc": {"balance": ctx.options.coin}}
                )
                await msg.edit(
                    f"You gave :coin: **{ctx.options.coin}** coins to **{user.username}**"
                )
            else:
                return await msg.edit(
                    "You have to mention someone you want to give your coins to"
                )
        else:
            setup_user(db, filter["userid"])
            await self.givecoin(ctx)
