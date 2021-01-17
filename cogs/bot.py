import asyncio
from datetime import datetime
from sqlite3 import IntegrityError

import discord
from discord.ext import commands
from discord.ext.menus import Menu, button, Button, Position
from toml import load

from ChatReviver import ChatReviver

# While this will be attached to the bot class, we need it to be top-level for the menu, so fuck it and load it twice
config = load("config.toml")
# Nice aliases as a result so oh well
default_prefixes = config["bot"]["default_prefixes"]
emoji = config["emoji"]


class Bot(commands.Cog):
    def __init__(self, bot: ChatReviver):
        self.bot = bot

    @commands.group(aliases=["prefixes"])
    async def prefix(self, ctx: commands.Context):
        if ctx.invoked_subcommand:
            return

        prefixes = await self.bot.fetch_prefixes(ctx.guild.id)

        embed = discord.Embed()
        embed.add_field(name="Default Prefixes",
                        value=", ".join([self.bot.user.mention] + [f"`{p}`" for p in default_prefixes]))
        embed.add_field(name="Custom Prefixes",
                        value=", ".join(f"`{p}`" for p in prefixes) if prefixes else "None")

        await ctx.send(embed=embed)

    @prefix.command()
    async def add(self, ctx: commands.Context, *, prefix: str):
        prefix = prefix.replace("`", "").replace("\n", "")[:16]

        try:
            if prefix in default_prefixes:
                raise IntegrityError

            async with self.bot.db.cursor() as cur:
                if (await cur.execute("SELECT count(*) FROM prefixes WHERE guild = $1", (ctx.guild.id,))).fetchone()[0] >= 10:
                    await ctx.message.add_reaction(config["emoji"]["cross"])
                    return await ctx.send("You can only have up to 10 custom prefixes at a time")

                await cur.execute("INSERT INTO prefixes VALUES ($1, $2)", (ctx.guild.id, prefix))

        except IntegrityError as e:  # SQLite 3 error handling is terrible
            if "UNIQUE constraint failed: prefixes.guild, prefixes.prefix" not in e.args:
                raise e

            await ctx.message.add_reaction(config["emoji"]["failure"])
            return await ctx.send("This prefix already exists")

        await ctx.message.add_reaction(config["emoji"]["success"])

    @prefix.command(alises=["delete"])
    async def remove(self, ctx: commands.Context):
        prefixes = await self.bot.fetch_prefixes(ctx.guild.id)

        if not prefixes:
            return await ctx.send("There are no custom prefixes for this server")

        embed = discord.Embed()
        embed.add_field(name="Custom Prefixes", value=", ".join(f"{i}.) `{p}`" for i, p in enumerate(prefixes, 1)))
        message = await ctx.send(embed=embed)

        menu = RemovePrefixMenu(message, len(prefixes))
        try:
            await menu.start(ctx, wait=True)
        except asyncio.TimeoutError:
            await menu.cancel()

        for i in menu.selected:
            await self.bot.db.execute("DELETE FROM prefixes WHERE guild = $1 AND prefix = $2",
                                      (ctx.guild.id, prefixes[i - 1]))


class RemovePrefixMenu(Menu):
    emoji_lookup = {i: f"{i}\N{combining enclosing keycap}" if i < 10 else "\N{keycap ten}" for i in range(1, 11)}

    def __init__(self, message: discord.Message, max_index: int):
        super().__init__(message=message)

        self.max = max_index
        self.selected = []
        self.add_reactions()

    def add_reactions(self):
        async def number_button(self, payload: discord.RawReactionActionEvent):
            number = next(k for k, v in self.emoji_lookup.items() if v == payload.emoji.name)
            if payload.event_type == "REACTION_ADD":
                self.selected.append(number)
            else:
                self.selected.remove(number)

        for i in range(1, self.max + 1):
            self.add_button(Button(self.emoji_lookup[i], number_button, position=Position(i)))

    async def clear_bot_reactions(self):
        for emoji in self.buttons:
            try:
                await self.message.remove_reaction(emoji, discord.Object(id=self.bot.user.id))
            except discord.HTTPException:
                continue

    @button(emoji["success"], position=Position(11))
    async def confirm(self, payload: discord.RawReactionActionEvent):
        if self.selected and payload.event_type == "REACTION_ADD":
            embed = self.message.embeds[0]
            embed.timestamp = datetime.now()
            embed.set_footer(text="Completed")
            await self.message.edit(embed=embed)

            await self.clear_bot_reactions()
            self.stop()

    @button(emoji["failure"], position=Position(12))
    async def cancel(self, _):
        embed = self.message.embeds[0]
        embed.timestamp = datetime.now()
        embed.set_footer(text="Cancelled")
        await self.message.edit(embed=embed)

        self.selected = []
        await self.clear_bot_reactions()
        self.stop()


def setup(bot):
    bot.add_cog(Bot(bot))
