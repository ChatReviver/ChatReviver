from aiohttp import web
from discord.ext import commands, tasks
from prometheus_client import Counter, Gauge
from prometheus_client import generate_latest, REGISTRY, CONTENT_TYPE_LATEST

OPCODES = {
    0: "DISPATCH",
    1: "HEARTBEAT",
    2: "IDENTIFY",
    3: "PRESENCE",
    4: "VOICE_STATE",
    5: "VOICE_PING",
    6: "RESUME",
    7: "RECONNECT",
    8: "REQUEST_MEMBERS",
    9: "INVALIDATE_SESSION",
    10: "HELLO",
    11: "HEARTBEAT_ACK",
    12: "GUILD_SYNC",
}

DISPATCHES = [
    "READY",
    "RESUMED",
    "MESSAGE_ACK",
    "MESSAGE_CREATE",
    "MESSAGE_DELETE",
    "MESSAGE_DELETE_BULK",
    "MESSAGE_UPDATE",
    "MESSAGE_REACTION_ADD",
    "MESSAGE_REACTION_REMOVE_ALL",
    "MESSAGE_REACTION_REMOVE",
    "PRESENCE_UPDATE",
    "USER_UPDATE",
    "CHANNEL_DELETE",
    "CHANNEL_UPDATE",
    "CHANNEL_CREATE",
    "CHANNEL_PINS_ACK",
    "CHANNEL_PINS_UPDATE",
    "CHANNEL_RECIPIENT_ADD",
    "CHANNEL_RECIPIENT_REMOVE",
    "GUILD_INTEGRATIONS_UPDATE",
    "GUILD_MEMBER_ADD",
    "GUILD_MEMBER_REMOVE",
    "GUILD_MEMBER_UPDATE",
    "GUILD_EMOJIS_UPDATE",
    "GUILD_CREATE",
    "GUILD_SYNC",
    "GUILD_UPDATE",
    "GUILD_DELETE",
    "GUILD_BAN_ADD",
    "GUILD_BAN_REMOVE",
    "GUILD_ROLE_CREATE",
    "GUILD_ROLE_DELETE",
    "GUILD_ROLE_UPDATE",
    "GUILD_MEMBERS_CHUNK",
    "VOICE_STATE_UPDATE",
    "VOICE_SERVER_UPDATE",
    "WEBHOOKS_UPDATE",
    "TYPING_START",
    "RELATIONSHIP_ADD",
    "RELATIONSHIP_REMOVE",
]


class Statistics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.app = web.Application()
        self.app.router.add_get("/metrics", self.get_metrics)

        self.metrics = {}
        bot.loop.create_task(self.start())

    async def start(self):
        self.add_metrics()

        runner = web.AppRunner(self.app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", 8000).start()

        self.loop.start()

    def add_metrics(self):
        for metric in [
            Counter("opcodes", "OP Codes recieved", ["opcode"]),
            Counter("dispatches", "Dispatched events recieved", ["event"]),
            Gauge("ws_latency", "Websocket Latency"),
            Gauge("guild_count", "Guild member count"),
            Gauge("member_count", "Total member count"),
            Counter("command_invokes", "Command invokes (but not necessarily completions)", ["command"])
        ]:
            self.metrics[metric._name] = metric

        # This will add all the OPcodes and dispatches before we get them. Unsure whether I want this
        # for name in OPCODES.values():
        #     self.metrics["OPCodes"].labels(opcode=name)
        #
        # for name in DISPATCHES:
        #     self.metrics["Dispatches"].labels(event=name)

    @staticmethod
    async def get_metrics(_):
        return web.Response(body=generate_latest(REGISTRY), headers={"Content-Type": CONTENT_TYPE_LATEST})

    @commands.Cog.listener()
    async def on_socket_response(self, data):
        opcode = data["op"]
        self.metrics["opcodes"].labels(opcode=OPCODES.get(opcode, opcode)).inc()

        if opcode == 0:
            self.metrics["dispatches"].labels(event=data["t"]).inc()

    @tasks.loop(seconds=15)
    async def loop(self):
        await self.bot.wait_until_ready()

        self.metrics["ws_latency"].set(self.bot.latency * 1000)
        self.metrics["guild_count"].set(len(self.bot.guilds))
        self.metrics["member_count"].set(sum(g.member_count for g in self.bot.guilds))

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.metrics["command_invokes"].labels(command=ctx.command.qualified_name).inc()


def setup(bot):
    bot.add_cog(Statistics(bot))
