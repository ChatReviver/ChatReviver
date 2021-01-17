from random import choice

import discord
from discord.ext import commands
from psutil import cpu_percent, cpu_freq, virtual_memory
from math import ceil

from ChatReviver import ChatReviver

invite_url = "https://discord.com/api/oauth2/authorize?client_id={}&scope=bot"


def random_shard_emoji(bot):
    return f"<:{choice(bot.config['emoji']['shards'])}>"


class Help(commands.Cog):
    """Help and info commands"""

    def __init__(self, bot: ChatReviver):
        self.bot = bot

    @commands.command()
    async def invite(self, ctx: commands.Context):
        await ctx.send(invite_url.format(self.bot.user.id))

    @commands.command()
    async def info(self, ctx: commands.Context):
        embed = discord.Embed(colour=discord.Colour(0x317c27),
                              description=f"Invite ChatReviver [here]({invite_url.format(self.bot.user.id)})!\n"
                                          "For more info on inviting the bot run r?invite or [see the docs](http://docs.chatreviver.gg/home/inviting_the_bot/)\n\u202b")

        embed.set_thumbnail(url=str(self.bot.user.avatar_url))
        embed.set_author(name="ChatReviver Info:")

        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Members", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        embed.add_field(name="🏓 Ping", value=f"{(self.bot.ws.latency * 1000):.0f}ms", inline=True)
        # embed.add_field(name="Shard", value=f"{ctx.guild.shard_id}/{self.bot.shard_count}", inline=True)
        embed.add_field(name=f"{random_shard_emoji(self.bot)}Shard", value="1/1", inline=True)  # We're not actually sharding yet lmao
        embed.add_field(name="CPU", value=f"{cpu_percent(interval=0.5)}% @ {cpu_freq().current / 1000:.2f}GHz", inline=True)
        gb = 1024 * 1024 * 1024
        embed.add_field(name="Memory", value=f"{(virtual_memory().used / gb):.1f}/{ceil(virtual_memory().total / gb)}GB", inline=True)

        await ctx.send(embed=embed)


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))
