import asyncio
import time
from datetime import datetime
import logging
from math import floor

import discord

from redbot.core import app_commands, commands, checks, Config, utils

__version__ = "1.0.0"
__author__ = "MarkSuckerberg"

log = logging.getLogger("red.SS13Status")

UNIX_DAYS = 60 * 60 * 24
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "Sol",
    8: "July",
    9: "August",
    10: "September",
    11: "October",
    12: "November",
    13: "December",
    14: "Year Day"
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
        self.serv.cancel()

@commands.hybrid_command()
async def fsctime(self, ctx):
    """
    Displays the current time in FSC
    """
    await ctx.send(await get_date())

@commands.hybrid_command()
@checks.admin_or_permissions(manage_guild=True)
async def setchannel(self, ctx, channel: discord.TextChannel):
    """
    Sets the channel to post the time in
    """
    cfg = self.config.guild(ctx.guild)
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

        await cached.edit(content=await get_date())

async def get_date():
    timestamp = datetime.utcnow().timestamp()
    days = floor(timestamp / UNIX_DAYS)
    years = floor(days / 365) + 481

    day_of_year = days % 365 + 1
    month_of_year = floor(day_of_year / 28)

    day_of_month = day_of_year % 28 + 1
    month_name = MONTH_NAMES[month_of_year]

    return f"{month_name} {day_of_month}, {years} FSC"
