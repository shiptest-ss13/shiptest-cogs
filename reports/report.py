import asyncio
from datetime import datetime
import logging
from typing import Union

from redbot.core import commands, Config, checks, app_commands
import discord

class Report(commands.Cog):
    im_doing_shit = False
    old_updates = {}

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 3257141233294, force_registration=True)

        default_global = {
            "admin_channel": None,
            "reports_channel": None
        }

        self.config.register_global(**default_global)

    @commands.hybrid_group()
    async def setReports(self, ctx: commands.Context):
        pass

    @setReports.command()
    async def adminChannel(self, ctx: commands.Context, newChannel: discord.TextChannel):
        try:
            if newChannel is not None:
                await self.config.admin_channel.set(newChannel.id)
                await ctx.send(f"Reports will be sent to: {newChannel.mention}")
            else:
                await self.config.admin_channel.set(None)
                await ctx.send("I will no longer relay reports.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the admin channel. Please check your entry and try again.")

    @setReports.command()
    async def reportsChannel(self, ctx: commands.Context, newChannel: discord.TextChannel):
        try:
            if newChannel is not None:
                await self.config.admin_channel.set(newChannel.id)
                await ctx.send(f"Reports will be recorded from: {newChannel.mention}")
            else:
                await self.config.admin_channel.set(None)
                await ctx.send("I will no longer relay reports.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the admin channel. Please check your entry and try again.")

    @commands.command()
    @commands.cooldown(1, 240, type=commands.BucketType.user)
    async def report(self, ctx: commands.Context, message: str = "", anonymous: bool = True):
        """
        Send a(n optionally anonymous) report to admins about staff behaviour.
        """
        await self.sendReport(message, anonymous, ctx.author.name)
        await ctx.message.delete()

    @app_commands.command(name="report", description="Send a report to the staff.")
    @app_commands.guild_only()
    async def report(self, interaction: discord.Interaction, message: str = "", anonymous: bool = True):
        """
        Send a(n optionally anonymous) report to admins about staff behaviour.
        """
        await self.sendReport(message, anonymous, interaction.user.name)
        await interaction.response.send_message("Report sent.", ephemeral=True)

    async def sendReport(self, message: str, anonymous: bool = True, username: str = None):
        channel = self.bot.get_channel(await self.config.admin_channel())

        name = "anonymous"
        if not anonymous:
            name = username

        embed = discord.Embed(title=f"Staff Feedback ({name})", description=f"{message}")
        await channel.send(embed=embed)

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        channel_id = await self.config.guild(message.guild).reports_channel()
        if message.channel.id != channel_id:
            return
        await self.report()
