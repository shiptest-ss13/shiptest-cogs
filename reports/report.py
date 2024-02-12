from redbot.core import commands, Config, checks, app_commands
import discord

class Report(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 3252041233294, force_registration=True)

        default_global = {
            "admin_channel": None,
            "reports_channel": None
        }

        self.config.register_global(**default_global)

    @commands.hybrid_group()
    @checks.mod_or_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def set_reports(self, ctx: commands.Context):
        pass

    @set_reports.command()
    async def admin_channel(self, ctx: commands.Context, newChannel: discord.TextChannel):
        try:
            if newChannel is not None:
                await self.config.admin_channel.set(newChannel.id)
                await ctx.send(f"Reports will be sent to: {newChannel.mention}")
            else:
                await self.config.admin_channel.set(None)
                await ctx.send("I will no longer relay reports.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the admin channel. Please check your entry and try again.")

    @set_reports.command()
    async def reports_channel(self, ctx: commands.Context, newChannel: discord.TextChannel):
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
    async def report(self, ctx: commands.Context, *args):
        """
        Send an anonymous report to admins about staff behaviour. The slash command is preferred.
        """
        message = " ".join(args)
        await self.sendReport(message, True, ctx.author.name)
        await ctx.message.delete()

    @app_commands.command(name="report", description="Send a report to the staff.")
    @app_commands.guild_only()
    async def slash_report(self, interaction: discord.Interaction, message: str = "", anonymous: bool = True):
        """
        Send a(n optionally anonymous) report to admins about staff behaviour.
        """
        await self.sendReport(message, anonymous, interaction.user.name)
        await interaction.response.send_message("Report sent.", ephemeral=True)

    async def send_report(self, message: str, anonymous: bool = True, username: str = None):
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
