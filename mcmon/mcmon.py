import asyncio
from datetime import datetime, timedelta
from logging import getLogger

import aiohttp
from discord import Color, Embed, Message, TextChannel
from redbot.core import Config, checks, commands

log = getLogger("red.mcmon")


class MCSrvStatus:
    def __init__(self, data):
        self.online = data["online"]
        self.motd = data["motd"]["clean"]
        self.hostname = data["hostname"]
        self.port = data["port"]
        self.version = data["version"]
        self.players_online = data["players"]["online"]
        self.players_max = data["players"]["max"]
        if "list" in data["players"]:
            self.players_list = data["players"]["list"]
        else:
            self.players_list = None
        self.icon = data["icon"]
        self.software = data["software"]

    @classmethod
    async def get_server_status(cls, server: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mcsrvstat.us/2/{server}") as resp:
                return MCSrvStatus(await resp.json())


class MCMon(commands.Cog):
    config: Config

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.add_listener(self.monitor, "on_guild_join")
        self.config = Config.get_conf(self, identifier=1234513213123)
        default_guild = {"enabled": False, "channel": None, "interval": 300, "servers": []}
        default_server = {"last_online": False, "server_message": None}
        self.config.register_guild(**default_guild)
        self.config.init_custom("server", 1)
        self.config.register_custom("server", **default_server)
        for guild in self.bot.guilds:
            self.bot.loop.create_task(self.monitor(guild))

    def cog_unload(self):
        self.bot.loop.create_task(self.config.clear_all_custom("server"))

    async def on_guild_join(self, guild):
        self.bot.loop.create_task(self.monitor(guild))

    @commands.group()
    @checks.admin_or_permissions(manage_guild=True)
    async def mcmon(self, ctx: commands.Context) -> None:
        """Minecraft server monitor"""
        pass

    @mcmon.command()
    async def add(self, ctx: commands.Context, server: str) -> None:
        """Add a server to monitor"""
        current = await self.config.guild(ctx.guild).servers()
        if server in current:
            await ctx.send("Server already exists")
            return
        current.append(server)
        await self.config.guild(ctx.guild).servers.set(current)
        await ctx.send("Server added")

    @mcmon.command()
    async def remove(self, ctx: commands.Context, server: str) -> None:
        """Remove a server from monitoring"""
        current = await self.config.guild(ctx.guild).servers()
        if server not in current:
            await ctx.send("Server does not exist")
            return
        current.remove(server)
        await self.config.guild(ctx.guild).servers.set(current)
        server_message = await self.config.custom("server", server).server_message()
        if server_message:
            channel = self.bot.get_channel(await self.config.guild(ctx.guild).channel())
            if channel:
                message = await channel.fetch_message(server_message)
                await message.delete()
        await ctx.send("Server removed")

    @mcmon.command()
    async def list(self, ctx: commands.Context) -> None:
        """List servers being monitored"""
        current = await self.config.guild(ctx.guild).servers()
        if not current:
            await ctx.send("No servers being monitored")
            return
        await ctx.send("Servers being monitored:\n" + "\n".join(current))

    @mcmon.command()
    async def channel(self, ctx: commands.Context, channel: TextChannel) -> None:
        """Set the channel to send notifications to"""
        current = await self.config.guild(ctx.guild).channel()
        if current != channel.id:
            old_channel: TextChannel = self.bot.get_channel(current)
            all_servers = await self.config.guild(ctx.guild).servers()
            for server in all_servers:
                server_message = await self.config.custom("server", server).server_message()
                if server_message:
                    message: Message = await old_channel.fetch_message(server_message)
                    await message.delete()
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send("Channel set")

    @mcmon.command()
    async def interval(self, ctx: commands.Context, interval: int) -> None:
        """Set the interval to check servers in seconds"""
        await self.config.guild(ctx.guild).interval.set(interval)
        await ctx.send("Interval set")

    @mcmon.command()
    async def start(self, ctx: commands.Context) -> None:
        """Start monitoring servers"""
        await self.config.guild(ctx.guild).enabled.set(True)
        await ctx.send("Monitoring started")

    @mcmon.command()
    async def stop(self, ctx: commands.Context) -> None:
        """Stop monitoring servers"""
        await self.config.guild(ctx.guild).enabled.set(False)
        await ctx.send("Monitoring stopped")

    @mcmon.command()
    async def status(self, ctx: commands.Context) -> None:
        """Check the status of the monitor"""
        enabled = await self.config.guild(ctx.guild).enabled()
        if enabled:
            await ctx.send("Monitoring is enabled")
        else:
            await ctx.send("Monitoring is disabled")

    async def monitor(self, guild) -> None:
        await self.bot.wait_until_ready()
        log.info("Starting monitor for %s", guild.name)
        while self is self.bot.get_cog("MCMon"):
            log.info("Checking servers for %s", guild.name)
            if await self.config.guild(guild).enabled():
                log.info("Monitoring enabled for %s", guild.name)
                servers = await self.config.guild(guild).servers()
                channel = self.bot.get_channel(await self.config.guild(guild).channel())
                if channel:
                    log.info("Channel found for %s", guild.name)
                    for server in servers:
                        status = await MCSrvStatus.get_server_status(server)
                        last_online = await self.config.custom("server", server).last_online()
                        if status.online:
                            embed = Embed(
                                title=f"{status.hostname}({status.version}) is online",
                                description=f"**MOTD:** {status.motd}\n"
                                f"**Players:** {status.players_online}/{status.players_max}\n"
                                f"**Software:** {status.software}"
                                f"**Last Updated:** <t:{datetime.utcnow().timestamp()}:R>",
                                color=Color.green(),
                            )
                            embed.add_field(
                                name="Players", value=("\n".join(status.players_list) if status.players_list else "Unknown")
                            )
                            await self.config.last_online.set(status.online)
                        else:
                            if last_online:
                                embed = Embed(
                                    title=f"{status.hostname} is offline",
                                    description=f"**Last online:** {last_online}",
                                    color=Color.red(),
                                )
                            else:
                                embed = None
                        server_message = await self.config.custom("server", server).server_message()
                        if server_message:
                            log.info("Server message found for %s", guild.name)
                            message = await channel.fetch_message(server_message)
                            await message.edit(embed=embed)
                        else:
                            log.info("Server message not found for %s", guild.name)
                            message = await channel.send(embed=embed)
                            await self.config.custom("server", server).server_message.set(message.id)
            await asyncio.sleep(await self.config.guild(guild).interval())
