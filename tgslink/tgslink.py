from asyncio import events
from datetime import datetime
import logging
from operator import contains
from tabnanny import check
from redbot.core import commands, Config
import discord
import tgsapi

log = logging.getLogger("red.tgslink")

class SS13Mon(commands.Cog):
	config: Config
	login_warned: list
	login_waiting: dict

	def cog_unload(self):
		return super().cog_unload()

	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.login_warned = list()
		self.login_waiting = dict()
		self.config = Config.get_conf(self, identifier=85416841231161, force_registration=True)

		def_guild = {
			"address": None,
		}

		def_member = {
			"token": None,
			"expiresAt": None,
		}

		self.config.register_guild(**def_guild)
		self.config.register_member(**def_member)

	async def check_logged_in(self, ctx):
		cfg = self.config.member(ctx.author)
		if((await cfg.token()) is None):
			await ctx.reply("Please log in")
			return False

		expires: datetime = await cfg.expiresAt()
		if(expires is None):
			await ctx.reply("Please log in")
			return False

		if(not (expires - datetime.now()).total_seconds()):
			await ctx.reply("Please log in")
			return False

		return True

	@commands.group()
	async def tgslink(self, ctx):
		pass

	@tgslink.command()
	async def launch(self, ctx: commands.Context, instance):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgsapi.tgs_watchdog_start(address, token, instance)
		if(not resp): await ctx.reply("Failed to launch watchdog")
		else: await ctx.reply("Requested Watchdog launch")

	@tgslink.command()
	async def shutdown(self, ctx: commands.Context, instance):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgsapi.tgs_watchdog_shutdown(address, token, instance)
		if(not resp): await ctx.reply("Failed to stop watchdog")
		else: await ctx.reply("Requested Watchdog shutdown")

	@tgslink.command()
	async def deploy(self, ctx: commands.Context, instance):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgsapi.tgs_dm_deploy(address, token, instance)
		if(not resp): await ctx.reply("Failed to start deployment")
		else: await ctx.reply("Started deployment")

	@tgslink.command()
	async def instances(self, ctx: commands.Context):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgsapi.tgs_instances(address, token)
		if(not resp):
			await ctx.reply("failed to get instance information")
			return
		resp: tgsapi.InstanceInformationQuery
		
		str_resp = "```"
		for instance in resp.content:
			str_resp += "{} - {}\n".format(instance.id, instance.name)
		str_resp += "```"
		await ctx.reply(str_resp)

	@tgslink.command()
	async def login(self, ctx: commands.Context, username, password):
		address = await self.config.guild(ctx.guild).address()

		resp = tgsapi.tgs_login(address, username, password)
		if(resp is None):
			await ctx.reply("Failed to login")
			try:
				await (await ctx.fetch_message()).delete()
			except:
				await ctx.reply("Failed to delete login message, please delete it manually.")
			return
		
		cfg = self.config.member(ctx.author)
		await cfg.token.set(resp[0])
		await cfg.expiresAt.set(resp[1])
		await ctx.reply("Logged in")
		try:
			await (await ctx.fetch_message()).delete()
		except:
			await ctx.reply("Failed to delete login message, please delete it manually.")
