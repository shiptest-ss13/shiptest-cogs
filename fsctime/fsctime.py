import asyncio
import time
from datetime import datetime
import logging
from math import floor

import discord

from redbot.core import commands, checks, Config

__version__ = "1.0.0"
__author__ = "MarkSuckerberg"

log = logging.getLogger("red.SS13Status")

UNIX_DAYS = 60 * 60 * 24
BYOND_EPOCH = datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()
MONTH_NAMES = {
    0: "January",
    1: "February",
    2: "March",
    3: "April",
    4: "May",
    5: "June",
    6: "Sol",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
    13: "Year Day"
}

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
    async def fsctime(self, ctx):
        """
        Displays the current time in FSC
        """
        date = self.get_date()
        time = datetime.utcnow().strftime("%H:%M")
        await ctx.send(f"{time}, {date}")

    @commands.hybrid_command()
    @checks.admin_or_permissions(manage_guild=True)
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """
        Sets the channel to post the time in
        """
        cfg = self.config.guild(ctx.guild)
        
        message = await channel.send("caching initial context")
        await cfg.message_id.set(message.id)

        await cfg.channel_id.set(channel.id)
        await ctx.send("Channel set!")

    @commands.hybrid_command()
    @checks.admin_or_permissions(manage_guild=True)
    async def setmessage(self, ctx, message: discord.Message):
        """
        Sets the message to update
        """
        cfg = self.config.guild(ctx.guild)
        await cfg.message_id.set(message.id)
        await ctx.send("Message set!")

    async def time_update_loop(self):
        for guild in self.bot.guilds:
            cfg = self.config.guild(guild)

            message = await cfg.message_id()
            channel = await cfg.channel_id()
            cached: discord.Message

            if(channel == None):
                continue

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

            await cached.edit(content=self.get_date())

        await asyncio.sleep(10)

    def get_date(self):
        timestamp = datetime.utcnow().timestamp() - BYOND_EPOCH #I hate this
        days = floor(timestamp / UNIX_DAYS)
        years = floor(days / 365) + 481

        day_of_year = days % 365 + 1
        month_of_year = floor(day_of_year / 28)

        day_of_month = day_of_year % 28 + 1
        month_name = MONTH_NAMES[month_of_year]

        return f"{month_name} {day_of_month}, {years} FSC"
