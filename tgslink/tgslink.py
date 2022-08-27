from redbot.core import commands, Config, checks
import logging

from .py_tgs.tgs_api_defs import tgs_login

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
			"token_expiration": None, # this is a timestamp
			"token_gh": None,
		}

		self._config.register_guild(**def_guild)
		self._config.register_member(**def_member)

	async def get_address(self, guild): return await self._config.guild(guild).address()
	async def try_delete(self, message):
		try:
			await message.delete()
		except:
			await message.reply("Failed to delete message, you must delete it manually!")

	@commands.group()
	async def tgslink(self, ctx): pass

	@tgslink.command()
	async def login(self, ctx, username = None, password = None):
		cfg = self._config.member(ctx.author)
		if((username is not None) ^ (password is not None)):
			await ctx.reply("Either both username and password must be supplied or neither!")
			await self.try_delete(ctx.message)
			return

		if(await cfg.pass_remember() and username is not None):
			log.info("saving login information for {}".format(ctx.author))
			await cfg.pass_username.set(username)
			await cfg.pass_password.set(password)

		if(username is None):
			log.info("no username provided")
			username = await cfg.pass_username()
			password = await cfg.pass_password()
			if(username is None or password is None):
				await ctx.reply("Login information is not saved!")
				await self.try_delete(ctx.message)
				return

		try:
			add = await self.get_address(ctx.guild)
			log.info("Attempting to login to {} with username {}".format(add, username))
			resp = tgs_login(add, username, password)
			await cfg.token_bearer.set(resp.Bearer)
			await cfg.token_expiration.set(resp.ExpiresAt.timestamp())
			await ctx.reply("Logged in")
		except Exception as a:
			log.exception("exception tying to log in", str(a))
			await ctx.reply("Failed to log in.")
		await self.try_delete(ctx.message)

	@tgslink.group()
	async def config(self, ctx): pass

	@config.command()
	async def remember_login(self, ctx):
		cfg = self._config.member(ctx.author)
		target = not await cfg.pass_remember()
		if(not target):
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
