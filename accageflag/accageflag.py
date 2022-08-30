from datetime import datetime, timedelta
import logging
from typing import Tuple
from discord import Member, AllowedMentions, User, TextChannel, Guild
from discord.abc import Snowflake
from redbot.core import commands, Config, checks
Context = commands.Context
log = logging.getLogger("red_aaf")


class AccountAgeFlagger(commands.Cog):
    """Class to manage flagging accounts under a specified age"""
    _config: Config

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._config = Config.get_conf(self, identifier=51362216380568, force_registration=True)

        def_guild = {
            "flag_role_id": None,
            "flag_channel_id": None,
            "verifier_role_id": None,
            "filter_age": None,
            "filter_age_seconds": None,
            "filter_pfp": None,
        }
        self._config.register_guild(**def_guild)

    @commands.Cog.listener("on_member_join")
    async def member_join(self, member: Member, force=False):
        log.info("Checking member for verification requirements")
        resp = await self.should_filter_member(member)
        if not resp[0] and not force:
            log.info(" Passed")
            return
        log.info("Failed")

        cfg = self._config.guild(member.guild)
        role_id = await cfg.flag_role_id()
        channel_id = await cfg.flag_channel_id()
        channel: TextChannel = await self.bot.fetch_channel(channel_id)
        verifier_id = await cfg.verifier_role_id()

        failed_to_add = False
        try:
            role = [f for f in await member.guild.fetch_roles() if f.id == role_id]
            await member.add_roles(role, atomic=True)
        except Exception as err:
            log.exception(err)
            failed_to_add = True

        reason = [resp[1], "forced"][force]
        message = f"Verification: <@&{verifier_id}> | {member.mention} has failed verification for the following reason: `{reason}`"
        if failed_to_add:
            message += "\n**And I failed to add the manual verification role!**"
        await channel.send(message, allowed_mentions=[None, AllowedMentions.none()][force])

    async def check_member_age(self, member: Snowflake):
        target = await self._config.guild(member.guild).filter_age_seconds()
        creation_delta: timedelta = datetime.utcnow() - member.created_at
        log.info(f"age is {creation_delta.total_seconds()}")
        if creation_delta.total_seconds() < target:
            return True
        return False

    async def check_member_pfp(self, member: User):
        log.info(f"pfp {not not member.avatar}")
        if not member.avatar:
            return True
        return False

    async def should_filter_member(self, member: Member) -> Tuple[bool, str]:
        cfg = self._config.guild(member.guild)
        if await cfg.filter_age() and await self.check_member_age(member):
            return tuple([True, "Member did not meet the age requirement"])
        if await cfg.filter_pfp() and await self.check_member_pfp(member):
            return tuple([True, "Member did not meet the pgp requirement"])
        return tuple([False, None])

    @commands.group()
    @checks.admin()
    async def aaf(self, ctx):
        pass

    @aaf.group()
    async def config(self, ctx):
        pass

    @config.command()
    async def flag_role_id(self, ctx: Context, value=None):
        cfg = self._config.guild(ctx.guild)
        cur = value or await cfg.flag_role_id()

        if value is None:
            await ctx.send(f"`flag_role_id: {cur}` (<@&{cur}>)", allowed_mentions=AllowedMentions.none())
            return

        await cfg.flag_role_id.set(int(value))
        await ctx.send(f"`flag_role_id: {cur}` (<@&{cur}>)", allowed_mentions=AllowedMentions.none())

    @config.command()
    async def verifier_role_id(self, ctx: Context, value=None):
        cfg = self._config.guild(ctx.guild)

        cur = value or await cfg.verifier_role_id()
        if value is None:
            await ctx.send(f"`verifier_role_id: {cur}` (<@&{cur}>)", allowed_mentions=AllowedMentions.none())
            return

        await cfg.verifier_role_id.set(int(value))
        await ctx.send(f"`verifier_role_id: {cur}` (<@&{cur}>)", allowed_mentions=AllowedMentions.none())

    @config.command()
    async def flag_channel_id(self, ctx: Context, value=None):
        cfg = self._config.guild(ctx.guild)

        cur = value or await cfg.flag_channel_id()
        if value is None:
            await ctx.send(f"`flag_channel_id: {cur}` (<#{cur}>)", allowed_mentions=AllowedMentions.none())
            return

        await cfg.flag_channel_id.set(int(value))
        await ctx.send(f"`flag_channel_id: {cur}` (<#{cur}>)", allowed_mentions=AllowedMentions.none())

    @config.command()
    async def filter_age_seconds(self, ctx: Context, value=None):
        cfg = self._config.guild(ctx.guild)

        cur = value or await cfg.filter_age_seconds()
        if value is None:
            await ctx.send(f"`filter_age_seconds: {cur}`", allowed_mentions=AllowedMentions.none())
            return

        await cfg.flag_role_id.set(int(value))
        await ctx.send(f"`filter_age_seconds: {cur}`", allowed_mentions=AllowedMentions.none())

    @config.command()
    async def all(self, ctx: Context):
        cfg = self._config.guild(ctx.guild)
        flag_role_id = await cfg.flag_role_id()
        verifier_role_id = await cfg.verifier_role_id()
        filter_age_seconds = await cfg.filter_age_seconds()

        await ctx.send(f"```\nflag_role_id = {flag_role_id}\nverifier_role_id = {verifier_role_id}\nfilter_age_seconds = {filter_age_seconds}\n```")

    @aaf.group()
    async def filter(self, ctx):
        pass

    @filter.command()
    async def check_age(self, ctx: Context):
        cfg = self._config.guild(ctx.guild)
        target = not await cfg.filter_age()
        resp = ["no longer", "now"][target]
        await ctx.send(f"Member age is {resp} being checked")

    @filter.command()
    async def check_pfp(self, ctx: Context):
        cfg = self._config.guild(ctx.guild)
        target = not await cfg.filter_pfp()
        resp = ["no longer", "now"][target]
        await ctx.send(f"Member having a valid profile picture is {resp} being checked")

    @aaf.command()
    async def force_self(self, ctx: Context):
        await self.member_join(ctx.author, force=True)
