from traceback import print_exc

import toml
from discord import TextChannel, AllowedMentions
from discord.ext import commands

from cogs.utils.asqlite import connect

try:
    __import__("uvloop").install()
except ImportError:
    pass


class ChatReviver(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.callable_prefix,
            max_messages=None, fetch_offline_member=False, guild_subscriptions=False,
            allowed_mentions=AllowedMentions(everyone=False, roles=False))

        self.config = toml.load("config.toml")
        if ids := self.config["bot"]["owner_ids"]:
            self.owner_ids = ids

        self.emoji = self.config["emoji"]

        self.db = self.loop.run_until_complete(connect("chatreviver.db", check_same_thread=False))

        self.load_extension("jishaku")
        for cog in ["dev", "bot", "reviver", "info"]:
            # noinspection PyBroadException
            try:
                self.load_extension("cogs." + cog)
            except Exception:
                print_exc()

        self.run(self.config["bot"]["token"])

    async def on_ready(self):
        print("=" * 35)
        print(f"Connected as {self.user} with id {self.user.id}")
        print(f"Loaded cogs {', '.join(self.cogs)}")
        print(f"Guild count: {len(self.guilds)}")
        print("=" * 35)

    async def on_message(self, message):
        if not isinstance(message.channel, TextChannel) or message.author.bot:
            return

        await self.process_commands(message)

    async def fetch_prefixes(self, guild: int):
        async with self.db.cursor() as cur:
            await cur.execute("SELECT prefix FROM prefixes WHERE guild = $1", (guild,))
            return [p["prefix"] for p in await cur.fetchall()]

    async def callable_prefix(self, bot, msg):
        prefixes = await self.fetch_prefixes(msg.guild.id)
        return commands.when_mentioned_or(*(self.config["bot"]["default_prefixes"] + prefixes))(bot, msg)


if __name__ == "__main__":
    ChatReviver()
