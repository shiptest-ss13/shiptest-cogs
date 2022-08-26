from redbot.core import commands, Config
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
			"pass_remember": False,
			"pass_username": None,
			"pass_password": None,
			"token_bearer": None,
			"token_expiration": None,
			"token_gh": None,
		}

		self._config.register_guild(**def_guild)
		self._config.register_member(**def_member)

	async def address(self, guild): return await self._config.guild(guild).address()
	async def try_delete(self, message):
		try:
			await message.delete()
		except:
			await message.reply("Failed to delete message, you must delete it manually!")

	@commands.group()
	async def tgslink(self, ctx): pass

	@tgslink.command()
	async def login(self, ctx, username, password):
		cfg = self._config.member(ctx.author)
		if(await cfg.pass_remember()):
			await cfg.pass_username.set(username)
			await cfg.pass_password.set(password)

		try:
			resp = tgs_login(self.address(ctx.guild), username, password)
			await cfg.token_bearer.set(resp.Bearer)
			await cfg.token_expiration.set(resp.ExpiresAt)
			await ctx.reply("Logged in")
		except:
			await ctx.reply("Failed to log in.")
		await self.try_delete(ctx.message)
