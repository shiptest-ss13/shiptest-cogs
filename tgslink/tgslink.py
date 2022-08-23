from cmath import exp
from datetime import datetime
from operator import indexOf
from typing import Tuple
from redbot.core import commands, Config
from json import JSONDecoder
import logging
import base64
import ssl
import requests

log = logging.getLogger("red.tgslink")

class TGSLink(commands.Cog):
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

		if(not (expires - datetime.utcnow()).total_seconds()):
			await ctx.reply("Please log in")
			return False

		return True

	@commands.group()
	async def tgslink(self, ctx):
		pass

	@tgslink.command()
	async def address(self, ctx: commands.Context, address):
		await self.config.guild(ctx.guild).address.set(address)
		await ctx.reply("Updated address.")

	@tgslink.command()
	async def launch(self, ctx: commands.Context, instance):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgs_watchdog_start(address, token, instance)
		if(not resp): await ctx.reply("Failed to launch watchdog")
		else: await ctx.reply("Requested Watchdog launch")

	@tgslink.command()
	async def shutdown(self, ctx: commands.Context, instance):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgs_watchdog_shutdown(address, token, instance)
		if(not resp): await ctx.reply("Failed to stop watchdog")
		else: await ctx.reply("Requested Watchdog shutdown")

	@tgslink.command()
	async def deploy(self, ctx: commands.Context, instance):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgs_dm_deploy(address, token, instance)
		if(not resp): await ctx.reply("Failed to start deployment")
		else: await ctx.reply("Started deployment")

	@tgslink.command()
	async def instances(self, ctx: commands.Context):
		if(not (await self.check_logged_in(ctx))): return
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgs_instances(address, token)
		if(not resp):
			await ctx.reply("failed to get instance information")
			return
		resp: InstanceInformationQuery
		
		str_resp = "```"
		for instance in resp.content:
			str_resp += "{} - {}\n".format(instance.id, instance.name)
		str_resp += "```"
		await ctx.reply(str_resp)

	@tgslink.command()
	async def login(self, ctx: commands.Context, username, password):
		address = await self.config.guild(ctx.guild).address()

		resp = tgs_login(address, username, password)
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

class InstanceInformation:
	accessible: bool
	path: str
	online: bool
	configurationType: int
	autoUpdateInterval: int
	chatBotLimit: int
	name: str
	id: int

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		self.accessible = dict["accessible"]
		self.path = dict["path"]
		self.online = dict["online"]
		self.configurationType = dict["configurationType"]
		self.autoUpdateInterval = dict["autoUpdateInterval"]
		self.chatBotLimit = dict["chatBotLimit"]
		self.name = dict["name"]
		self.id = dict["id"]
		return self
	
	def __str__(self) -> str:
		return "Instance-{}/'{}'".format(self.id, self.name)

class InstanceInformationQuery:
	content: 'list[InstanceInformation]'
	totalPages: int
	pageSize: int
	totalItems: int

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		self.totalPages = dict["totalPages"]
		self.pageSize = dict["pageSize"]
		self.totalItems = dict["totalItems"]
		self.content = list()
		for iJson in dict["content"]:
			self.content.append(InstanceInformation().decode(iJson))
		return self

class TGSUserInformation:
	id: int
	name: Tuple[str, None] = None

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		self.id = dict["id"]
		if("name" in dict.keys()): self.name = dict["name"]
		return self

class JobInformation:
	startedBy: TGSUserInformation
	description: str
	errorCode: Tuple[int, None] = None
	exceptionDetails: Tuple[str, None] = None
	startedAt: datetime
	stoppedAt: Tuple[datetime, None] = None
	cancelled: bool
	cancelRightsType: int
	cancelRight: int
	id: int
	progress: int
	stage: str

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		self.startedBy = TGSUserInformation().decode(dict["startedBy"])
		self.description = dict["description"]
		self.startedAt = dict["startedAt"]
		self.cancelled = dict["cancelled"]
		self.cancelRightsType = dict["cancelRightsType"]
		self.cancelRight = dict["cancelRight"]
		self.id = dict["id"]
		if("errorCode" in dict.keys()): self.errorCode = dict["errorCode"]
		if("exceptionDetails" in dict.keys()): self.exceptionDetails = dict["exceptionDetails"]
		if("stoppedAt" in dict.keys()): self.stoppedAt = dict["stoppedAt"]
		if("progress" in dict.keys()): self.progress = dict["progress"]
		if("stage" in dict.keys()): self.stage = dict["stage"]
		return self

class JobInformationQuery:
	content: 'list[JobInformation]'
	totalPages: int
	pageSize: int
	totalItems: int

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		self.totalPages = dict["totalPages"]
		self.pageSize = dict["pageSize"]
		self.totalItems = dict["totalItems"]
		self.content = list()
		for iJson in dict["content"]:
			self.content.append(JobInformation().decode(iJson))
		return self

class WatchdogStatus:
	status: int
	softRestart: bool
	softShutdown: bool
	autoStart: bool
	allowWebClient: bool
	visibility: int
	securityLevel: int
	port: int
	startupTimeout: int
	heartbeatSeconds: int
	topicRequestTimeout: int
	additionalParameters: str

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		self.status = dict["status"]
		self.softRestart = dict["softRestart"]
		self.softShutdown = dict["softShutdown"]
		self.autoStart = dict["autoStart"]
		self.allowWebClient = dict["allowWebClient"]
		self.visibility = dict["visibility"]
		self.securityLevel = dict["securityLevel"]
		self.port = dict["port"]
		self.startupTimeout = dict["startupTimeout"]
		self.heartbeatSeconds = dict["heartbeatSeconds"]
		self.topicRequestTimeout = dict["topicRequestTimeout"]
		self.additionalParameters = dict["additionalParameters"]
		return self

	def is_online(self) -> bool: return self.status != 0

def make_request(address: str, method = "get", headers = None, json = None) -> requests.Response:
	ssl_context = [None, ssl.create_default_context()][address.startswith("https://")]
	return requests.request(method, address, headers=headers, json=json)

def tgs_request(address, path = "/", method = "get", token = None, json = None, headers: 'dict[str,str]' = None):
	_headers = {"Api": "Tgstation.Server.Api/9.3.0", "User-Agent": "TGSLink/1.0", "accept": "application/json"}
	if(token): _headers["Authorization"] = "Bearer {}".format(token)
	if(headers is not None):
		for key in headers.keys():
			_headers[key] = headers[key]
	return make_request("{}{}".format(address, path), method, _headers, json)

def tgs_server_info(address, token):
	return tgs_request(address, "/Administration", token=token)

def tgs_login(address, username, password) -> Tuple[Tuple[str, datetime], None]:
	basic = base64.b64encode("{}:{}".format(username, password).encode("ascii")).decode("ascii")
	resp = tgs_request(address, method="post", headers={"Authorization": "Basic {}".format(basic)})
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	resp = resp.json()
	expStr = resp["expiresAt"].split(".")[0]
	return tuple([resp["bearer"], datetime.strptime(expStr, "%Y-%m-%dT%H:%M:%S")])

def tgs_instances(address, token) -> Tuple[InstanceInformationQuery, None]:
	resp = tgs_request(address, "/Instance/List", token=token)
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=InstanceInformationQuery)

def tgs_get_instance(address, token, instance) -> Tuple[InstanceInformation, None]:
	resp = tgs_request(address, "/Instance/{}".format(instance), token=token)
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=InstanceInformation)

def tgs_dm_deploy(address, token, instance) -> Tuple[JobInformation, None]:
	resp = tgs_request(address, "/DreamMaker", method="put", token=token, headers={"Instance": "{}".format(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformation)

def tgs_job_get(address, token, instance, jobid) -> Tuple[JobInformation, None]:
	resp = tgs_request(address, "/Job/{}".format(jobid), token=token, headers={"Instance": "{}".format(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformation)

def tgs_job_all(address, token, instance) -> Tuple[JobInformationQuery, None]:
	resp = tgs_request(address, "/Job/List", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformationQuery)

def tgs_watchdog_status(address, token, instance) -> Tuple[WatchdogStatus, None]:
	resp = tgs_request(address, "/DreamDaemon", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=WatchdogStatus)

def tgs_watchdog_start(address, token, instance) -> Tuple[JobInformation, None]:
	resp = tgs_request(address, "/DreamDaemon", method="put", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformation)

def tgs_watchdog_shutdown(address, token, instance) -> Tuple[bool, None]:
	resp = tgs_request(address, "/DreamDaemon", method="delete", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		print("Failed to run query: {}".format(resp.reason))
		return None
	return resp.status_code == 204
