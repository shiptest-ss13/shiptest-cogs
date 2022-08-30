import asyncio
from datetime import datetime, timedelta
import logging
from typing import List, Tuple
from discord import Member, AllowedMentions, TextChannel, Role, Guild, Message
from discord.abc import Snowflake
from redbot.core import commands, Config, checks
Context = commands.Context
log = logging.getLogger("red.AccountAgeFlagger")


class AccountAgeFlagger(commands.Cog):
    """Class to manage flagging accounts under a specified age"""
    _config: Config
    joins_this_minute: List[Member] = list()
    joins_minute_target: int = 0
    joins_raid_triggered: bool = False
    processing_all: bool = False

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
            "filter_raid": None,
            "raid_join_cutoff": None,
        }
        def_member = {
            "already_filtered": None,
        }
        self._config.register_guild(**def_guild)
        self._config.register_member(**def_member)

    @commands.Cog.listener("on_member_join")
    async def member_join(self, member: Member, force=False):
        cfg = self._config.guild(member.guild)
        mem_cfg = self._config.member(member)

        time = datetime.utcnow()
        if self.joins_minute_target != time.minute:
            self.joins_minute_target = time.minute
            self.joins_raid_triggered = False
            self.joins_this_minute = list()
        if not self.processing_all:
            self.joins_this_minute.append(member)

        channel_id = await cfg.flag_channel_id()
        channel: TextChannel = await self.bot.fetch_channel(channel_id)
        if self.joins_raid_triggered:
            await channel.edit(topic=f"Raid in Progress {len(self.joins_this_minute)}/{await cfg.raid_join_cutoff()}")
        else:
            await channel.edit(topic=f"Monitoring: {len(self.joins_this_minute)}/{await cfg.raid_join_cutoff()}")

        if await mem_cfg.already_filtered() and not force and not self.joins_raid_triggered:
            return
        await mem_cfg.already_filtered.set(True)

        log.info("Checking member for verification requirements")
        resp = await self.should_filter_member(member)
        if not resp[0] and not force:
            log.info(" Passed")
            return
        log.info("Failed")

        verifier_id = await cfg.verifier_role_id()

        reason = [resp[1], "forced"][not resp[0]]
        message = f"Verification: <@&{verifier_id}> | {member.mention} has failed verification for the following reason: `{reason}`"
        if not await self.filter_member(member):
            message += "\n**And I failed to add the manual verification role!**"
        await channel.send(message, allowed_mentions=AllowedMentions.none())

    async def filter_member(self, member: Member) -> bool:
        role_id = await self._config.guild(member.guild).flag_role_id()
        failed_to_add = False
        try:
            role: Role = member.guild.get_role(role_id)
            log.info(f"role: {role.name} : {role.id}")
            await member.add_roles(role)
        except Exception as err:
            log.exception(err)
            failed_to_add = True
        return not failed_to_add

    async def check_member_age(self, member: Snowflake):
        target = await self._config.guild(member.guild).filter_age_seconds()
        creation_delta: timedelta = datetime.utcnow() - member.created_at
        if creation_delta.total_seconds() < target:
            return True
        return False

    async def check_member_pfp(self, member: Member):
        has_avatar = not not member.avatar
        return not has_avatar

    async def check_member_raid(self, member: Member):
        if self.joins_raid_triggered:
            return True
        if len(self.joins_this_minute) >= await self._config.guild(member.guild).raid_join_cutoff():
            self.joins_raid_triggered = True
            for member_stored in self.joins_this_minute:
                if member_stored.id == member.id:
                    continue
                await self.member_join(member_stored)
            return True
        return False

    async def should_filter_member(self, member: Member) -> Tuple[bool, str]:
        cfg = self._config.guild(member.guild)
        if await cfg.filter_age() and await self.check_member_age(member):
            return tuple([True, "Member did not meet the age requirement"])
        if await cfg.filter_pfp() and await self.check_member_pfp(member):
            return tuple([True, "Member did not meet the pgp requirement"])
        if not self.processing_all and await cfg.filter_raid() and await self.check_member_raid(member):
            return tuple([True, "Member was caught in a raid trap"])
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

        await cfg.filter_age_seconds.set(int(value))
        await ctx.send(f"`filter_age_seconds: {cur}`", allowed_mentions=AllowedMentions.none())

    @config.command()
    async def raid_join_cutoff(self, ctx: Context, value=None):
        cfg = self._config.guild(ctx.guild)

        cur = value or await cfg.raid_join_cutoff()
        if value is None:
            await ctx.send(f"`raid_join_cutoff: {cur}`", allowed_mentions=AllowedMentions.none())
            return

        await cfg.raid_join_cutoff.set(int(value))
        await ctx.send(f"`raid_join_cutoff: {cur}`", allowed_mentions=AllowedMentions.none())

    @aaf.group()
    async def filter(self, ctx):
        pass

    @filter.command()
    async def check_age(self, ctx: Context):
        cfg = self._config.guild(ctx.guild)
        target = not await cfg.filter_age()
        await cfg.filter_age.set(target)
        resp = ["no longer", "now"][target]
        await ctx.send(f"Member age is {resp} being checked")

    @filter.command()
    async def check_pfp(self, ctx: Context):
        cfg = self._config.guild(ctx.guild)
        target = not await cfg.filter_pfp()
        await cfg.filter_pfp.set(target)
        resp = ["no longer", "now"][target]
        await ctx.send(f"Member having a valid profile picture is {resp} being checked")

    @filter.command()
    async def check_raid(self, ctx: Context):
        cfg = self._config.guild(ctx.guild)
        target = not await cfg.filter_raid()
        await cfg.filter_raid.set(target)
        resp = ["no longer", "now"][target]
        await ctx.send(f"Member raids are {resp} being checked")

    @aaf.command()
    async def force_self(self, ctx: Context):
        await self.member_join(ctx.author, force=True)

    @aaf.command()
    async def run_on(self, ctx: Context, target_id, force=False):
        guild: Guild = ctx.guild
        member = await guild.fetch_member(target_id)
        await self.member_join(member, force)
        await ctx.send(f"Ran on {member}")

    @aaf.command()
    @checks.is_owner()
    async def filter_all(self, ctx: Context):
        tally = 0
        message: Message = await ctx.send("Caching")
        guild: Guild = ctx.guild
        all_members = await guild.fetch_members(limit=None).flatten()
        total = len(all_members)
        self.processing_all = True
        for member in all_members:
            if not (tally % 10):
                pct = f"{((tally / total) * 100)}%"
                await message.edit(content=f"Processed {tally} ({pct})")
                await asyncio.sleep(0.25)
            tally += 1
            await self.member_join(member)
        self.processing_all = False
        await message.delete()
        await ctx.send("Processing all members completed.")
