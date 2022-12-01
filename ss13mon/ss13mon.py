import asyncio
from datetime import datetime, timedelta
import logging
import random
from sys import stdout
from threading import Timer
from time import time
import discord
from redbot.core import commands, Config, checks, utils
import socket
import struct
import urllib.parse

log = logging.getLogger("red.ss13mon")

class SS13Mon(commands.Cog):
	config: Config
	_tasks: 'list[asyncio.Task]'

	def cog_unload(self):
		for task in self._tasks:
			task.cancel()
		return super().cog_unload()

	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self._tasks = list()
		self.config = Config.get_conf(self, identifier=854168416161, force_registration=True)

		def_guild = {
			"update_interval": 10,
			"update_hash": None,
			"channel": None,
			"address": None,
			"public_address": None,
			"port": None,
			"port_auth": None,
			"message_id": None,
			"message_id_auth": None,
			# internal status values
			"last_roundid": None,
			"last_title": None,
			"last_online": None,
			"last_online_auth": None,
		}
		self.config.register_guild(**def_guild)
		for guild in self.bot.guilds:
			self.start_guild_update_loop(guild)

	def start_guild_update_loop(self, guild):
		task = asyncio.get_event_loop().create_task(self.update_guild_message(guild))
		self._tasks.append(task)
		task.add_done_callback(self._handle_task_completion)

	def _handle_task_completion(self, future: asyncio.Task):
		self._tasks.remove(future)

	@commands.command()
	@commands.cooldown(1, 5)
	async def ss13status(self, ctx: commands.Context):
		await ctx.channel.send(embed=(await self.generate_embed(ctx.guild)))
	
	@commands.group()
	@checks.admin()
	async def ss13mon(self, ctx: commands.Context):
		pass

	@ss13mon.command()
	async def current(self, ctx: commands.Context):
		cfg = self.config.guild(ctx.guild)
		address = await cfg.address()
		port =  await cfg.port()
		channel =  await cfg.channel()
		port_auth = await cfg.port_auth()
		update_interval =  await cfg.update_interval()
		await ctx.send("Current Config: ```\naddress: {}\nport: {}\nauth port: {}\nchannel: {}\nupdate_interval: {}\n```".format(address, port, port_auth, channel, update_interval))
	
	@ss13mon.command()
	async def address(self, ctx: commands.Context, value = None):
		cfg = self.config.guild(ctx.guild)
		await cfg.address.set(value)
		await ctx.send("Updated the config entry for address.")

	@ss13mon.command()
	async def public_address(self, ctx, value):
		cfg = self.config.guild(ctx.guild)
		await cfg.public_address.set(value)
		await ctx.send("Updated the config entry for public_address.")

	@ss13mon.command()
	async def port(self, ctx: commands.Context, value = None):
		cfg = self.config.guild(ctx.guild)
		await cfg.port.set(value)
		await ctx.send("Updated the config entry for port.")
	
	@ss13mon.command()
	async def port_auth(self, ctx: commands.Context, value = None):
		cfg = self.config.guild(ctx.guild)
		await cfg.port_auth.set(value)
		await ctx.send("Updated the config entry for the auth port.")
	
	@ss13mon.command()
	async def channel(self, ctx: commands.Context, value = None):
		await self.delete_message(ctx.guild)
		cfg = self.config.guild(ctx.guild)
		if(not value == None): value = int(value)
		await cfg.channel.set(value)
		await ctx.send("Update the config entry for address and deleted the old message if found.")

	@ss13mon.command()
	async def update(self, ctx: commands.Context):
		self.start_guild_update_loop(ctx.guild)
		await ctx.send("Forced a guild update.")

	@ss13mon.command()
	async def update_interval(self, ctx: commands.Context, value = None):
		cfg = self.config.guild(ctx.guild)
		await cfg.update_interval.set((int(value), None)[value == None])
		await ctx.send("Changed the update interval, consider forcing an update to reset the active Timer")

	async def generate_embed(self, guild: discord.Guild):
		cfg = self.config.guild(guild)
		address = await cfg.address()
		port = await cfg.port()
		if(isinstance(port, str)): port = int(port)

		if(address == None or port == None):
			return discord.Embed(type="rich", title="FAILED TO GENERATE EMBED", timestamp=datetime.utcnow(), description="ADDRESS OR PORT NOT SET")

		status = await self.query_server(address, port)
		if(status == None):
			last_roundid = (await cfg.last_roundid()) or "Unknown"
			last_title = (await cfg.last_title()) or "Failed to fetch data"
			last_online = await cfg.last_online() or "Unknown"
			if(isinstance(last_online, float)): last_online = datetime.fromtimestamp(last_online)
			return discord.Embed(type="rich", color=discord.Colour.red(), title=last_title, timestamp=datetime.utcnow()).add_field(name="Server Offline", value="Last Round: `{}`\nLast Seen: `{}`".format(last_roundid, last_online))

		roundid = int(*status["round_id"])
		servtitle = str(*status["version"])
		await self.config.guild(guild).last_roundid.set(roundid)
		duration = int(*status['round_duration'])
		duration = str(timedelta(seconds=duration))
		player_count = int(*status["players"])
		time_dilation_avg = float(*status["time_dilation_avg"])
		try:
			players: list[str] = (await self.query_server("localhost", port, "?whoIs"))["players"]
			players.sort()
		except:
			players = list()

		await cfg.last_roundid.set(roundid)
		await cfg.last_title.set(servtitle)
		await cfg.last_online.set(time())

		update_interval = await cfg.update_interval()
		if(update_interval == None):
			update_interval = 0
		embbie: discord.Embed = discord.Embed(type="rich", color=discord.Colour.blue(), title=servtitle, timestamp=datetime.utcnow())

		public_address = await cfg.public_address()
		value_inf = "Round ID: `{}`\nPlayers: `{}`\nDuration: `{}`\nTIDI: `{}%`\nNext Update: `{}`\nJoin: <byond://{}:{}/>".format(roundid, player_count, duration, time_dilation_avg, ("{}s".format(update_interval), "Disabled")[update_interval == 0], public_address, port)
		embbie.add_field(name="Server Information", value=value_inf)

		field_visi = "Visible Players ({})".format(len(players))
		value_visi = "```{}```".format(", ".join(players))
		embbie.add_field(name=field_visi, value=value_visi)

		return embbie
	
	async def generate_auth_embed(self, guild: discord.Guild):
		cfg = self.config.guild(guild)
		address = await cfg.address()
		port = await cfg.port_auth()
		if(isinstance(port, str)): port = int(port)
		if(address == None or port == None):
			return discord.Embed(type="rich", title="FAILED TO GENERATE EMBED", timestamp=datetime.utcnow(), description="ADDRESS OR PORT NOT SET")
		
		status = await self.query_server(address, port)
		if(status == None):
			last_online = await cfg.last_online_auth() or "Unknown"
			if(isinstance(last_online, float)): last_online = datetime.fromtimestamp(last_online)
			return discord.Embed(type="rich", color=discord.Colour.red(), title="Auth Server", timestamp=datetime.utcnow()).add_field(name="Auth Server Offline", value="Last Seen: `{}`".format(last_online))
		await cfg.last_online_auth.set(time())

		public_address = await cfg.public_address()
		return discord.Embed(type="rich", color=discord.Colour.blue(), title="Auth server", timestamp=datetime.utcnow()).add_field(name="Join", value="<byond://{}:{}/>".format(public_address, port))

	async def query_server(self, game_server:str, game_port:int, querystr="?status" ) -> dict:
		"""
		Queries the server for information
		"""
		conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 

		try:
			query = b"\x00\x83" + struct.pack('>H', len(querystr) + 6) + b"\x00\x00\x00\x00\x00" + querystr.encode() + b"\x00" #Creates a packet for byond according to TG's standard
			conn.settimeout(20) #Byond is slow, timeout set relatively high to account for any latency
			conn.connect((game_server, game_port)) 

			conn.sendall(query)

			data = conn.recv(4096) #Minimum number should be 4096, anything less will lose data

			parsed_data = urllib.parse.parse_qs(data[5:-1].decode())

			return parsed_data
			
		except (ConnectionRefusedError, socket.gaierror, socket.timeout):
			return None #Server is likely offline

		finally:
			conn.close()

	async def update_guild_message(self, guild: discord.Guild, depth = 1):
		try:
			local_hash = str(random.random())
			cfg = self.config.guild(guild)
			await cfg.update_hash.set(local_hash)

			channel = await cfg.channel()
			if(channel == None):
				return
			channel: discord.TextChannel = guild.get_channel(channel)
			if(isinstance(channel, discord.TextChannel) == False):
				return

			message = await cfg.message_id()
			cached: discord.Message
			if(message == None):
				if(isinstance(message, str)): message = int(message)
				cached = await channel.send("caching initial context")
				await cfg.message_id.set(cached.id)
			else:
				try:
					cached = await channel.fetch_message(message)
				except(discord.NotFound):
					cached = await channel.send("caching initial context")
					await cfg.message_id.set(cached.id)
			
			message_auth = await cfg.message_id_auth()
			cached_auth: discord.Message
			if(message_auth == None):
				cached_auth = await channel.send("caching initial context")
				await cfg.message_id_auth.set(cached_auth.id)
			else:
				if(isinstance(message_auth, str)): message_auth = int(message_auth)
				try:
					cached_auth = await channel.fetch_message(message_auth)
				except(discord.NotFound):
					cached_auth = await channel.send("caching initial context")
					await cfg.message_id_auth.set(cached_auth.id)

			await cached.edit(content=None, embed=(await self.generate_embed(guild)))
			await cached_auth.edit(content=None, embed=(await self.generate_auth_embed(guild)))

		except Exception as err:
			log.error("Encountered an exception when attempting to update guild message: '{}'".format(str(err)))
		update_interval = await cfg.update_interval()
		if(update_interval == None or update_interval == 0):
			return

		await asyncio.sleep(update_interval)
		actual_hash = await cfg.update_hash()
		if(actual_hash != local_hash): # command was run again while we were sleeping
			return
		
		if(depth > 5):
			self.start_guild_update_loop(guild)
			return

		try:
			await self.update_guild_message(guild, depth + 1)
		except RecursionError:
			self.start_guild_update_loop(guild)

	async def delete_message(self, guild: discord.Guild):
		cfg = self.config.guild(guild)
		channel = await cfg.channel()
		if(channel == None):
			return
		channel: discord.TextChannel = guild.get_channel(channel)
		if(isinstance(channel, discord.TextChannel) == False):
			return

		message = await cfg.message_id()
		cached: discord.Message
		if(message == None):
			return
		else:
			try:
				cached = await channel.fetch_message(message)
			except(discord.NotFound):
				return

		await cached.delete()
