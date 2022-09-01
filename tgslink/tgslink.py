import asyncio
from datetime import datetime
from math import floor
from redbot.core import commands, Config, checks
import logging
from discord import Message
from github import Github

from tgslink.py_tgs.tgs_api_discord import job_to_embed
from tgslink.py_tgs.tgs_api_models import TgsModel_DreamDaemonRequest, TgsModel_ErrorMessageResponse, TgsModel_RepositoryUpdateRequest, TgsModel_TestMergeParameters

from .py_tgs.tgs_api_defs import tgs_dd_launch, tgs_dd_stop, tgs_dd_update, tgs_dm_compile_job_list, tgs_dm_deploy, tgs_job_cancel, tgs_job_get, tgs_login, tgs_repo_status, tgs_repo_update, tgs_repo_update_tms

log = logging.getLogger("red.tgslink")


class TGSLink(commands.Cog):
    _config: Config

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._config = Config.get_conf(self, identifier=85416841231161, force_registration=True)

        def_guild = {
            "address": None,
        }

        def_member = {
            "pass_remember": None,
            "pass_username": None,
            "pass_password": None,
            "token_bearer": None,
            "token_expiration": None,  # this is a timestamp
            "token_gh": None,
        }

        self._config.register_guild(**def_guild)
        self._config.register_member(**def_member)

    async def get_address(self, guild):
        return await self._config.guild(guild).address()

    async def get_token(self, ctx):
        cfg = self._config.member(ctx.author)
        exp = await cfg.token_expiration()
        dif = (exp - datetime.utcnow().timestamp()) if exp is not None else None
        if dif is None or dif < 1:
            log.info("token is expired")
            if not await self._login(ctx):
                log.info("and we failed to refresh it")
                return None
        return await cfg.token_bearer()

    async def try_delete(self, message: Message):
        try:
            await message.delete()
        except Exception:
            await message.reply("Failed to delete message, you must delete it manually!")

    @commands.group()
    async def tgslink(self, ctx):
        pass

    @tgslink.command()
    @checks.is_owner()
    async def force_expire(self, ctx):
        cfg = self._config.member(ctx.author)
        await cfg.token_expiration.set(0)
        await ctx.send("Forced token expiration")

    async def _login(self, ctx, username=None, password=None) -> bool:
        cfg = self._config.member(ctx.author)

        if username is None or password is None:
            log.info("logging in with no user or pass")
            if not await cfg.pass_remember():
                log.info("they don't want shit saved")
                return False
            username = await cfg.pass_username()
            password = await cfg.pass_password()
            if username is None or password is None:
                log.info("they don't have shit saved")
                return False

        try:
            resp = tgs_login(await self.get_address(ctx.guild), username, password)
            await cfg.token_bearer.set(resp.Bearer)
            await cfg.token_expiration.set(resp.ExpiresAt.timestamp())
            log.info("logged them in")
            return True
        except Exception as e:
            log.exception(e)
            return False

    @tgslink.command()
    async def login(self, ctx, username=None, password=None):
        cfg = self._config.member(ctx.author)
        if (username is not None) ^ (password is not None):
            await ctx.reply("Either both username and password must be supplied or neither!")
            await self.try_delete(ctx.message)
            return

        if await cfg.pass_remember() and username is not None:
            log.info("saving login information for {}".format(ctx.author))
            await cfg.pass_username.set(username)
            await cfg.pass_password.set(password)

        try:
            if await self._login(ctx, username, password):
                await ctx.reply("Logged in")
            else:
                await ctx.reply("Failed to log in.")
        except Exception:
            await ctx.reply("Failed to log in.")
        await self.try_delete(ctx.message)

    @tgslink.group()
    async def config(self, ctx):
        pass

    @config.command()
    async def remember_login(self, ctx):
        cfg = self._config.member(ctx.author)
        target = not await cfg.pass_remember()
        if not target:
            await cfg.pass_username.set(None)
            await cfg.pass_password.set(None)
        await cfg.pass_remember.set(target)
        await ctx.reply("Login details are {} being saved.".format(["no longer", "now"][target]))

    @config.command()
    @checks.admin()
    async def address(self, ctx, address):
        cfg = self._config.guild(ctx.guild)
        await cfg.address.set(address)
        await ctx.reply("Updated address!")

    @config.command()
    async def gh_token(self, ctx, gh_token):
        cfg = self._config.member(ctx.author)
        await cfg.gh_token.set(gh_token)
        await ctx.reply("Updated your GH Token")
        await self.try_delete(ctx.message)

    @tgslink.group()
    async def job(self, ctx):
        pass

    @job.command()
    async def get(self, ctx, instance, job_id):
        resp = tgs_job_get(await self.get_address(ctx.guild), await self.get_token(ctx), instance, job_id)
        await ctx.reply(embed=job_to_embed(resp))

    @job.command()
    async def cancel(self, ctx, instance, job_id):
        try:
            resp = tgs_job_cancel(await self.get_address(ctx.guild), await self.get_token(ctx), instance, job_id)
            await ctx.reply(embed=job_to_embed(resp))
        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to cancel job: ({})='{}'".format(err._status_code, err.Message))

    @tgslink.group()
    async def dm(self, ctx):
        pass

    @dm.command()
    async def deploy(self, ctx: commands.Context, instance=1):
        try:
            status = tgs_dm_compile_job_list(await self.get_address(ctx.guild), await self.get_token(ctx), instance)[0]
            if not status.Job.StoppedAt:
                await ctx.reply("There is already a deployment in progress!")
                return

            job = tgs_dm_deploy(await self.get_address(ctx.guild), await self.get_token(ctx), instance)
            msg: Message = await ctx.reply("```Caching```\n")

            while not job.StoppedAt:
                await asyncio.sleep(0.5)
                try:
                    job = tgs_job_get(await self.get_address(ctx.guild), await self.get_token(ctx), instance, job.Id)
                except TgsModel_ErrorMessageResponse as err:
                    if err._status_code == 401:
                        await msg.edit(content="Token no longer valid, please login again. Waiting two seconds...")
                    else:
                        raise err
                try:
                    await msg.edit(content="```\nProgress: {} ({}%)\nStage: {}\n```\n".format(self.progress_bar(job.Progress), job.Progress, job.Stage or "N/A"))
                except Exception:
                    break

            if job.ok():
                await msg.edit(content="Deployment Completed")
            elif job.Cancelled:
                await msg.edit(content="Deployment Cancelled")
            else:
                await msg.edit(content="Deployment Failed\n```{}```\n".format(job.ExceptionDetails))

        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to request deployment: {}|{}".format(err._status_code, err.Message))

    def progress_bar(self, pct, len=10, empty_char="□", filled_char="■"):
        actual = floor(pct / 10)
        return (filled_char * actual) + (empty_char * (len - actual))

    @tgslink.group()
    async def repo(self, ctx):
        pass

    @repo.command()
    async def active_tms(self, ctx, instance=1):
        try:
            resp = tgs_repo_status(await self.get_address(ctx.guild), await self.get_token(ctx), instance)
            if not resp.ok():
                await ctx.send("I failed to fetch the repository status! ({})".format(resp._status_code))
                return
            gh = Github().get_repo(f"{resp.RemoteRepositoryOwner}/{resp.RemoteRepositoryName}")
            reply = "Active TMs:\n```\n"
            for tm in resp.RevisionInformation.ActiveTestMerges:
                gh_pr = gh.get_pull(tm.Number)
                update_avail = gh_pr.head.sha != tm.TargetCommitSha
                reply += "#{}{} - {} - @{}\n".format([" ", "!"][update_avail], tm.Number, tm.TitleAtMerge, tm.TargetCommitSha)
            reply += "```\n"
            await ctx.reply(reply)
        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to query TMs: {}|{}".format(err._status_code, err.Message))

    @repo.command()
    async def update_active_tms(self, ctx, instance=1):
        try:
            if tgs_repo_update_tms(await self.get_address(ctx.guild), await self.get_token(ctx), instance):
                await ctx.reply("Updated all TMs")
            else:
                await ctx.reply("Failed to update TMs")
        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to update TMs: {}|{}".format(err._status_code, err.Message))

    @repo.command()
    async def test_merge(self, ctx, pr_num, instance=1):
        try:
            current = tgs_repo_status(await self.get_address(ctx.guild), await self.get_token(ctx), instance)
            req = TgsModel_RepositoryUpdateRequest()
            req.NewTestMerges = list()
            for active in current.RevisionInformation.ActiveTestMerges:
                if active.Id == pr_num:
                    await ctx.send("That is already TMd")
                    return
            tm = TgsModel_TestMergeParameters()
            tm.Number = int(pr_num)
            tm.Comment = "TGSLink Automatic Test Merge"
            req.NewTestMerges.append(tm)
            resp = tgs_repo_update(await self.get_address(ctx.guild), await self.get_token(ctx), instance, req)
            if resp.ActiveJob is None:
                await ctx.send("Test Merge did not create a job, error?")
                return
            job = tgs_job_get(await self.get_address(ctx.guild), await self.get_token(ctx), instance, resp.ActiveJob.Id)
            while not job.StoppedAt:
                await asyncio.sleep(0.5)
                job = tgs_job_get(await self.get_address(ctx.guild), await self.get_token(ctx), instance, job.Id)
            if job.ok():
                await ctx.send("Test merged!")
                return
            await ctx.send("Failed to test merge: `{}`".format(job.ExceptionDetails))
        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to update TMs: {}|{}".format(err._status_code, err.Message))

    @tgslink.group()
    async def dd(self, ctx):
        pass

    @dd.command()
    async def launch(self, ctx, instance=1):
        try:
            if tgs_dd_launch(await self.get_address(ctx.guild), await self.get_token(ctx), instance):
                await ctx.reply("Instance launched")
            else:
                await ctx.reply("Failed to launch instance!")
        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to launch the watchdog: {}|{}".format(err._status_code, err.Message))

    @dd.command()
    async def graceful(self, ctx, enabled=True, instance=1):
        try:
            req = TgsModel_DreamDaemonRequest()
            req.SoftShutdown = enabled
            resp = tgs_dd_update(await self.get_address(ctx.guild), await self.get_token(ctx), req, instance)
            await ctx.reply("Graceful is now {}".format(["disabled", "enabled"][not not resp.SoftShutdown]))
        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to update the watchdog: {}|{}".format(err._status_code, err.Message))

    @dd.command()
    async def shutdown(self, ctx, instance=1):
        try:
            if tgs_dd_stop(await self.get_address(ctx.guild), await self.get_token(ctx), instance):
                await ctx.reply("Instance stopped")
            else:
                await ctx.reply("Failed to stop instance!")
        except TgsModel_ErrorMessageResponse as err:
            await ctx.reply("Failed to stop the watchdog: {}|{}".format(err._status_code, err.Message))
