import json

import discord
from discord.ext import commands

from ChatReviver import ChatReviver


class Dev(commands.Cog):
    def __init__(self, bot: ChatReviver):
        self.bot = bot

    @commands.is_owner()
    @commands.command(aliases=["echo"])
    async def say(self, ctx, *, message):
        await ctx.send(message)

    @commands.is_owner()
    @commands.command()
    async def msgtext(self, ctx, msg: discord.Message):
        embed = discord.Embed(timestamp=msg.created_at, colour=hash(msg.author.id) % (1 << 24))

        author_name = f"{msg.author.display_name} • {msg.author}" if msg.author.nick else msg.author
        embed.set_author(name=author_name, icon_url=str(msg.author.avatar_url))
        embed.set_footer(text=f"#{msg.channel} in {msg.guild}")

        embed.description = "```" + msg.content.replace("```", "\n") + "```"
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command()
    async def msgraw(self, ctx, msg: discord.Message):
        raw = await ctx.bot.http.get_message(msg.channel.id, msg.id)
        raw = json.dumps(raw, indent=2, ensure_ascii=False, sort_keys=True).replace("```", "\n")
        await ctx.send(f"```json\n{raw}```")


def setup(bot):
    bot.add_cog(Dev(bot))
