import asyncio
import time
from datetime import datetime
import logging
from math import floor

import discord

from redbot.core import commands, checks, Config, app_commands

__version__ = "1.0.0"
__author__ = "MarkSuckerberg"

log = logging.getLogger("red.SS13Status")

UNIX_DAYS = 60 * 60 * 24
BYOND_EPOCH = datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()
MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "Sol",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Year Day"
]
WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

class FSCTime(commands.Cog):

    def __init__(self, bot):
        self.time_loop = None

        self.bot = bot
        self.config = Config.get_conf(self, 3047293194, force_registration=True)

        default_guild = {
            "message_id": None,
            "channel_id": None,
        }

        self.config.register_guild(**default_guild)
        self.time_loop = bot.loop.create_task(self.time_update_loop())
    
    def cog_unload(self):
        self.time_loop.cancel()

    @commands.hybrid_command()
    async def fsctime(self, ctx, timestamp: int = None):
        """
        Displays the current time in FSC
        """
        if(timestamp == None):
            time = datetime.utcnow()
        else:
            time = datetime.fromtimestamp(timestamp)
        await ctx.send(content=None, embed=self.generate_embed(time))

    @commands.guild_only()
    @commands.hybrid_group()
    @checks.admin_or_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def setfsctime(self, ctx):
        """
        Configuration group for the SS13 status command
        """
        pass

    @setfsctime.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """
        Sets the channel to post the time in
        """
        cfg = self.config.guild(ctx.guild)
        
        message = await channel.send(content=None, embed=self.generate_embed())
        await cfg.message_id.set(message.id)

        await cfg.channel_id.set(channel.id)
        await ctx.send("Channel set!")

    @setfsctime.command()
    async def setmessage(self, ctx, message: discord.Message):
        """
        Sets the message to update
        """
        cfg = self.config.guild(ctx.guild)
        await cfg.message_id.set(message.id)
        await ctx.send("Message set!")

    @setfsctime.command()
    async def current(self, ctx):
        """
        Shows the current settings
        """
        cfg = self.config.guild(ctx.guild)
        message = await cfg.message_id()
        channel = await cfg.channel_id()
        await ctx.send(f"Channel: {channel}\nMessage: {message}")

    async def time_update_loop(self):
        while self == self.bot.get_cog("FSCTime"):
            for guild in self.bot.guilds:
                cfg = self.config.guild(guild)

                message = await cfg.message_id()
                channel = await cfg.channel_id()

                if(channel == None):
                    continue

                channel: discord.TextChannel = guild.get_channel(channel)
                cached: discord.Message = None

                if(message == None):
                    if(isinstance(message, str)): 
                        message = int(message)
                    cached = await channel.send("caching initial context")
                    await cfg.message_id.set(cached.id)
                else:
                    try:
                        cached = await channel.fetch_message(message)
                    except(discord.NotFound):
                        cached = await channel.send("caching initial context")
                        await cfg.message_id.set(cached.id)

                await cached.edit(content=None, embed=self.generate_embed(datetime.utcnow()))

            # Sleep until the next minute
            await asyncio.sleep(61 - datetime.utcnow().second)

    def generate_embed(self, time = None):
        if(time == None):
            time = datetime.utcnow()
        embed = discord.Embed(title="Current Sector Time", description=f"{time.strftime('%H:%M')}\n{self.get_date(time)}", timestamp=time, color=0x00ff00)
        return embed

    def get_date(self, time = None):
        if(time == None):
            time = datetime.utcnow()
        timestamp = time.timestamp() - BYOND_EPOCH #I hate this
        days = floor(timestamp / UNIX_DAYS)
        years = floor(days / 365) + 481

        day_of_year = days % 365 + 1
        month_of_year = floor(day_of_year / 28)

        day_of_month = day_of_year % 28 + 1
        month_name = MONTH_NAMES[month_of_year]

        weekday = floor(day_of_year / 7) % 7
        weekday_name = WEEKDAY_NAMES[weekday]

        return f"{weekday_name} {month_name} {day_of_month}, {years} FSC"
