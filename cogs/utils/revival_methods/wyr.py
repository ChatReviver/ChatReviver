import csv
from random import choice

import discord
from discord.ext import commands
from discord.ext.menus import Menu, button


class WouldYouRather(Menu):
    with open("cogs/utils/revival_methods/wouldyourather.csv", newline="\n") as f:
        questions = [q for q in csv.reader(f, delimiter=",", quotechar='"')]

    reactors = ([], [])

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
        question = choice(self.questions)
        em = discord.Embed(title=question[0])

        em.add_field(name="Option 🅰", value=question[1])
        em.add_field(name="Option 🅱", value=question[2])

        em.add_field(name="\u202b\n🅰", value="\u202b", inline=False)
        em.add_field(name="🅱", value="\u202b")

        message = await channel.send(embed=em)
        return message

    async def update_reactors(self, payload: discord.RawReactionActionEvent):
        a = str(payload.emoji) == "🅰"

        try:
            if payload.event_type == "REACTION_ADD":
                self.reactors[0 if a else 1].append(payload.user_id)
                self.reactors[1 if a else 0].remove(payload.user_id)

                await self.message.remove_reaction("🅱" if a else "🅰", discord.Object(id=payload.user_id))
            else:
                self.reactors[0 if a else 1].remove(payload.user_id)
        except ValueError:
            pass

        em = self.message.embeds[0]
        fmt = ", ".join([self.ctx.bot.get_user(m).name for m in (self.reactors[0] if a else self.reactors[1])])

        fmt = fmt if fmt else "\u202b"
        fmt = fmt if len(fmt) < 250 else "A lot of members!"

        em.set_field_at(2 if a else 3, name="\u202b\n🅰" if a else "🅱", value=fmt, inline=False)
        await self.message.edit(embed=em)

    @button("🅰")
    async def a(self, payload):
        await self.update_reactors(payload)

    @button("🅱")
    async def b(self, payload):
        await self.update_reactors(payload)
