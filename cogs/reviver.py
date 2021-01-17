import asyncio
import typing
from collections import namedtuple
from datetime import timedelta

import discord
from discord.ext import commands

from ChatReviver import ChatReviver
from cogs.utils.converters import timeout_parser
from cogs.utils.revival_methods.topic import topic
from cogs.utils.revival_methods.wyr import WouldYouRather


class Reviver(commands.Cog):
    def __init__(self, bot: ChatReviver):
        self.bot = bot

    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 60 * 5, commands.BucketType.guild)
    @commands.cooldown(10, 60 * 60 * 1, commands.BucketType.guild)
    @commands.command(aliases=["wyr"])
    async def wouldyourather(self, ctx: commands.Context):
        await WouldYouRather(timeout=60 * 60 * 24).start(ctx, wait=True)

    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 60 * 5, commands.BucketType.guild)
    @commands.cooldown(10, 60 * 60 * 1, commands.BucketType.guild)
    @commands.command()
    async def topic(self, ctx: commands.Context):
        await topic(ctx.channel)

    # TODO: Move this to global error handler when that gets made
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.add_reaction(ctx.bot.config["emoji"]["failure"])
            return await ctx.send(f"This command is on cooldown for another {error.retry_after:.0f} seconds")

        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.message.add_reaction(ctx.bot.config["emoji"]["failure"])
            return await ctx.send(f"This command can only be used in one [PLACEHOLDER] at a time")


def channel_has_reviver():
    async def predicate(ctx: commands.Context):
        async with ctx.bot.db.cursor() as cur:
            has_reviver = (await cur.execute("SELECT * FROM revivers WHERE guild = $1 and channel = $2",
                                             (ctx.guild.id, ctx.channel.id))).fetchone() is not None

        if not has_reviver:
            await ctx.message.add_reaction(ctx.bot.config["emoji"]["tick"])
            await ctx.send("You have tried to modify the reviver for this channel but one is not set up! "
                           "To set up a reviver for this channel, see the docs: ...")
            return False

        else:
            return True

    return commands.check(predicate)


class Timeout(commands.Cog):
    def __init__(self, bot: ChatReviver):
        self.bot = bot
        self.tasks = {}

    def cog_check(self, ctx: commands.Context):
        return commands.has_guild_permissions(manage_channels=True)

    @commands.group()
    async def reviver(self, ctx: commands.Context):
        if ctx.invoked_subcommand:
            return
        return await ctx.send("This command requires subcommands to do anything. See the docs for help: ...")

    @reviver.command(alises=["set_up"])
    async def setup(self, ctx: commands.Context):
        ...

    @channel_has_reviver()
    @reviver.command()
    async def enable(self, ctx: commands.Context):
        await self.bot.db.execute("UPDATE revivers SET enabled = 1 WHERE guild = $1 and channel = $2",
                                  (ctx.guild.id, ctx.channel.id))

        await ctx.message.add_reaction(self.bot.config["emoji"]["tick"])

    @channel_has_reviver()
    @reviver.command()
    async def disable(self, ctx):
        await self.bot.db.execute("UPDATE revivers SET enabled = 0 WHERE guild = $1 and channel = $2",
                                  (ctx.guild.id, ctx.channel.id))

        await ctx.message.add_reaction(self.bot.config["emoji"]["tick"])

    @channel_has_reviver()
    @reviver.command()
    async def timeout(self, ctx: commands.Context, *, timeout: typing.Optional[timeout_parser]):
        if timeout < timedelta(hours=1) or timeout > timedelta(days=7):
            await ctx.message.add_reaction(self.bot.config["emoji"]["failure"])
            return await ctx.send("The timeout cannot be less than 1 hour or larger than 7 days")

        timeout = timeout.seconds if not timeout.days else timeout.days * (60 * 60 * 24)

        await self.bot.db.execute("UPDATE revivers SET timeout = $1 WHERE guild = $2 AND channel = $3",
                                  (timeout, ctx.guild.id, ctx.channel.id))

        self.spawn_timeout_task(ctx.channel, timeout)
        await ctx.message.add_reaction(self.bot.config["emoji"]["tick"])

    @channel_has_reviver()
    @reviver.command()
    async def mode(self, ctx: commands.Context, *, mode):
        ...

    """
    So the timeout system works by spawning a task per channel (with a timeout) which sleeps for the timeout
    If anyone sends a message to this channel, cancel the timeout and respawn it
    If the sleep finishes then the timeout has been reached so revive the channel
    The task will also be cancelled if the timeout length is updated or disabled
    """

    # TODO: There's a lot of caching that could be done to improve this system

    Reviver = namedtuple("Reviver", ("task", "timeout"))

    async def timeout_task(self, channel: discord.TextChannel, timeout: int):
        try:
            await asyncio.sleep(timeout)

            print(f"Timeout in {channel}")

        except asyncio.CancelledError:
            return

    def spawn_timeout_task(self, channel: discord.TextChannel, timeout: int = None):
        if reviver := self.tasks.get(channel.id):
            # If this function is called because the timeout has been updated, cancel the task and spawn a new one
            reviver.task.cancel()

            if timeout is None:
                # Timeout has not been changed via the command so use previous value for timeout
                timeout = reviver.timeout

        task = self.bot.loop.create_task(self.timeout_task(channel, timeout))
        self.tasks[channel.id] = self.Reviver(task, timeout)

    @commands.Cog.listener()
    async def on_ready(self):
        async with self.bot.db.cursor() as cur:
            for row in (await cur.execute("SELECT channel, timeout FROM revivers")).fetchall():
                self.spawn_timeout_task(self.bot.get_channel(row["channel"]), row["timeout"])

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.TextChannel) or message.author.bot:
            return

        # Someone has sent a message so cancel and restart the task
        self.spawn_timeout_task(message.channel)


def setup(bot):
    bot.add_cog(Reviver(bot))
    bot.add_cog(Timeout(bot))
