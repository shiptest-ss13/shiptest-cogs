import asyncio
from cmath import exp
from datetime import datetime
from operator import indexOf
from time import sleep
from typing import Dict, Tuple
from redbot.core import commands, Config
from json import JSONDecoder, JSONEncoder
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
			"gh_token": None,
		}

		self.config.register_guild(**def_guild)
		self.config.register_member(**def_member)

	async def check_logged_in(self, ctx):
		cfg = self.config.member(ctx.author)
		if((await cfg.token()) is None):
			await ctx.reply("Please log in")
			return False

		expires: float = await cfg.expiresAt()
		if(expires is None):
			await ctx.reply("Please log in")
			return False

		if((expires - datetime.utcnow().timestamp()) <= 0):
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
	async def gh_token(self, ctx: commands.Context, gh_token):
		await self.config.member(ctx.author).gh_token.set(gh_token)
		await ctx.reply("GH Token updated")
		try:
			await ctx.message.delete()
		except:
			await ctx.reply("Failed to delete command. Delete it yourself.")

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
				await ctx.message.delete()
			except:
				await ctx.reply("Failed to delete login message, please delete it manually.")
			return
		
		cfg = self.config.member(ctx.author)
		await cfg.token.set(resp[0])
		await cfg.expiresAt.set(resp[1])
		await ctx.reply("Logged in")
		try:
			await ctx.message.delete()
		except:
			await ctx.reply("Failed to delete login message, please delete it manually.")
	
	@tgslink.command()
	async def repo_status(self, ctx: commands.Context, instance):
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgs_repo_status(address, token, instance)
		if(resp is None):
			await ctx.reply("Failed to fetch repo information")
			return
		resp: RepositoryStatus
		
		resp_str = "Repository Information\n```\n"
		resp_str += "Remote: {}/{}\n".format(resp.remoteRepositoryOwner, resp.remoteRepositoryName)
		resp_str += "SHA: {}\n".format(resp.revisionInformation.commitSha)
		resp_str += "```\n"
		await ctx.reply(resp_str)
	
	@tgslink.command()
	async def repo_tms(self, ctx: commands.Context, instance):
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		resp = tgs_repo_status(address, token, instance)
		if(resp is None):
			await ctx.reply("Failed to fetch repo information")
			return
		resp: RepositoryStatus

		resp_str = "Test Merges\n```\n"
		for tm in resp.revisionInformation.activeTestMerges:
			resp_str += "{} - {} @ {}\n".format(tm.number, tm.titleAtMerge, tm.targetCommitSha)
		resp_str += "```\n"
		await ctx.reply(resp_str)

	@tgslink.command()
	async def repo_pr_info(self, ctx: commands.Context, instance, pr_id):
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		gh_token = await self.config.member(ctx.author).gh_token()
		resp = tgs_repo_status(address, token, instance)
		if(resp is None):
			await ctx.reply("Failed to fetch repo information")
			return
		resp: RepositoryStatus

		pr: GHPullRequest = gh_get_pr(resp.remoteRepositoryOwner, resp.remoteRepositoryName, pr_id, gh_token)
		if(pr is None):
			await ctx.reply("Failed to fetch PR information")
			return
		
		resp_str = "PR - {}\n```\n".format(pr.number)
		resp_str += "Title: {}\n".format(pr.title)
		resp_str += "State: {}\n".format(pr.state)
		resp_str += "SHA: {}\n".format(pr.head.sha)
		resp_str += "```\n"
		await ctx.reply(resp_str)

	@tgslink.command()
	async def repo_update_tms(self, ctx: commands.Context, instance, update_from_origin=True):
		address = await self.config.guild(ctx.guild).address()
		token = await self.config.member(ctx.author).token()
		gh_token = await self.config.member(ctx.author).gh_token()
		if(not tgs_repo_update_tms(address, token, instance, gh_token, update_from_origin)): await ctx.reply("Failed to update TMs")
		else: await ctx.reply("Updated TMs")

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
	startedBy: TGSUserInformation = None
	description: str = None
	errorCode: Tuple[int, None] = None
	exceptionDetails: Tuple[str, None] = None
	startedAt: datetime = None
	stoppedAt: Tuple[datetime, None] = None
	cancelled: bool = None
	cancelRightsType: int = None
	cancelRight: int = None
	id: int = None
	progress: int = None
	stage: str = None

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
	content: 'list[JobInformation]' = None
	totalPages: int = None
	pageSize: int = None
	totalItems: int = None

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
	status: int = None
	softRestart: bool = None
	softShutdown: bool = None
	autoStart: bool = None
	allowWebClient: bool = None
	visibility: int = None
	securityLevel: int = None
	port: int = None
	startupTimeout: int = None
	heartbeatSeconds: int = None
	topicRequestTimeout: int = None
	additionalParameters: str = None

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

class TestMerge:
	id: int = None
	mergedAt: datetime = None
	titleAtMerge: str = None
	bodyAtMerge: str = None
	url: str = None
	author: str = None
	number: int = None
	targetCommitSha: str = None
	comment: str = None

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		if("id" in dict.keys()): self.id = dict["id"]
		if("mergedAt" in dict.keys()): self.mergedAt = dict["mergedAt"]
		if("titleAtMerge" in dict.keys()): self.titleAtMerge = dict["titleAtMerge"]
		if("bodyAtMerge" in dict.keys()): self.bodyAtMerge = dict["bodyAtMerge"]
		if("url" in dict.keys()): self.url = dict["url"]
		if("author" in dict.keys()): self.author = dict["author"]
		if("number" in dict.keys()): self.number = dict["number"]
		if("targetCommitSha" in dict.keys()): self.targetCommitSha = dict["targetCommitSha"]
		if("comment" in dict.keys()): self.comment = dict["comment"]
		return self

class RevisionInformation:
	originCommitSha: str
	timestamp: datetime
	commitSha: str
	activeTestMerges: 'list[TestMerge]'

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		if("originCommitSha" in dict.keys()): self.originCommitSha = dict["originCommitSha"]
		if("timestamp" in dict.keys()): self.timestamp = dict["timestamp"]
		if("commitSha" in dict.keys()): self.commitSha = dict["commitSha"]
		if("activeTestMerges" in dict.keys()):
			self.activeTestMerges = list()
			for entry in dict["activeTestMerges"]:
				self.activeTestMerges.append(TestMerge().decode(entry))
		return self

class RepositoryStatus:
	origin: str = None
	remoteGitProvider: int = None
	remoteRepositoryOwner: str = None
	remoteRepositoryName: str = None
	activeJob: JobInformation = None
	reference: str = None
	committerName: str = None
	committerEmail: str = None
	accessUser: str = None
	pushTestMergeCommits: bool = None
	createGithubDeployments: bool = None
	showTestMergeCommitters: bool = None
	autoUpdatesKeepTestMerges: bool = None
	postTestMergeComment: bool = None
	updateSubmodules: bool = None
	revisionInformation: RevisionInformation = None

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		if("origin" in dict.keys()): self.origin = dict["origin"]
		if("remoteGitProvider" in dict.keys()): self.remoteGitProvider = dict["remoteGitProvider"]
		if("remoteRepositoryOwner" in dict.keys()): self.remoteRepositoryOwner = dict["remoteRepositoryOwner"]
		if("remoteRepositoryName" in dict.keys()): self.remoteRepositoryName = dict["remoteRepositoryName"]
		if("activeJob" in dict.keys()): self.activeJob = dict["activeJob"]
		if("reference" in dict.keys()): self.reference = dict["reference"]
		if("committerName" in dict.keys()): self.committerName = dict["committerName"]
		if("committerEmail" in dict.keys()): self.committerEmail = dict["committerEmail"]
		if("accessUser" in dict.keys()): self.accessUser = dict["accessUser"]
		if("pushTestMergeCommits" in dict.keys()): self.pushTestMergeCommits = dict["pushTestMergeCommits"]
		if("createGithubDeployments" in dict.keys()): self.createGithubDeployments = dict["createGithubDeployments"]
		if("showTestMergeCommitters" in dict.keys()): self.showTestMergeCommitters = dict["showTestMergeCommitters"]
		if("autoUpdatesKeepTestMerges" in dict.keys()): self.autoUpdatesKeepTestMerges = dict["autoUpdatesKeepTestMerges"]
		if("postTestMergeComment" in dict.keys()): self.postTestMergeComment = dict["postTestMergeComment"]
		if("updateSubmodules" in dict.keys()): self.updateSubmodules = dict["updateSubmodules"]
		if("revisionInformation" in dict.keys()): self.revisionInformation = RevisionInformation().decode(dict["revisionInformation"])
		return self

class TestMergeParamaters:
	number: int
	targetCommitSha: str
	comment: str

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		if("number" in dict.keys()): self.number = dict["number"]
		if("targetCommitSha" in dict.keys()): self.targetCommitSha = dict["targetCommitSha"]
		if("comment" in dict.keys()): self.comment = dict["comment"]
		return self
	
	def encode(self, dict: dict):
		dict.clear()
		if(self.number is not None): dict["number"] = self.number
		if(self.targetCommitSha is not None): dict["targetCommitSha"] = self.targetCommitSha
		if(self.comment is not None): dict["comment"] = self.comment
		return dict

class RepositoryUpdateRequest:
	checkoutSha: str = None
	updateFromOrigin: bool = None
	reference: str = None
	committerName: str = None
	committerEmail: str = None
	accessUser: str = None
	accessToken: str = None
	pushTestMergeCommits: bool = None
	createGithubDeployments: bool = None
	showTestMergeCommitters: bool = None
	autoUpdatesKeepTestMerges: bool = None
	autoUpdatesSynchronize: bool = None
	postTestMergeComment: bool = None
	updateSubmodules: bool = None
	newTestMerges: 'list[TestMergeParamaters]' = None

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		if("checkoutSha" in dict.keys()): self.checkoutSha = dict["checkoutSha"]
		if("updateFromOrigin" in dict.keys()): self.updateFromOrigin = dict["updateFromOrigin"]
		if("reference" in dict.keys()): self.reference = dict["reference"]
		if("committerName" in dict.keys()): self.committerName = dict["committerName"]
		if("committerEmail" in dict.keys()): self.committerEmail = dict["committerEmail"]
		if("accessUser" in dict.keys()): self.accessUser = dict["accessUser"]
		if("accessToken" in dict.keys()): self.accessToken = dict["accessToken"]
		if("pushTestMergeCommits" in dict.keys()): self.pushTestMergeCommits = dict["pushTestMergeCommits"]
		if("createGithubDeployments" in dict.keys()): self.createGithubDeployments = dict["createGithubDeployments"]
		if("showTestMergeCommitters" in dict.keys()): self.showTestMergeCommitters = dict["showTestMergeCommitters"]
		if("autoUpdatesKeepTestMerges" in dict.keys()): self.autoUpdatesKeepTestMerges = dict["autoUpdatesKeepTestMerges"]
		if("autoUpdatesSynchronize" in dict.keys()): self.autoUpdatesSynchronize = dict["autoUpdatesSynchronize"]
		if("postTestMergeComment" in dict.keys()): self.postTestMergeComment = dict["postTestMergeComment"]
		if("updateSubmodules" in dict.keys()): self.updateSubmodules = dict["updateSubmodules"]
		return self
	
	def encode(self, _dict: dict):
		_dict.clear()
		if(self.checkoutSha is not None): _dict["checkoutSha"] = self.checkoutSha
		if(self.updateFromOrigin is not None): _dict["updateFromOrigin"] = self.updateFromOrigin
		if(self.reference is not None): _dict["reference"] = self.reference
		if(self.committerName is not None): _dict["committerName"] = self.committerName
		if(self.committerEmail is not None): _dict["committerEmail"] = self.committerEmail
		if(self.accessUser is not None): _dict["accessUser"] = self.accessUser
		if(self.accessToken is not None): _dict["accessToken"] = self.accessToken
		if(self.pushTestMergeCommits is not None): _dict["pushTestMergeCommits"] = self.pushTestMergeCommits
		if(self.createGithubDeployments is not None): _dict["createGithubDeployments"] = self.createGithubDeployments
		if(self.showTestMergeCommitters is not None): _dict["showTestMergeCommitters"] = self.showTestMergeCommitters
		if(self.autoUpdatesKeepTestMerges is not None): _dict["autoUpdatesKeepTestMerges"] = self.autoUpdatesKeepTestMerges
		if(self.autoUpdatesSynchronize is not None): _dict["autoUpdatesSynchronize"] = self.autoUpdatesSynchronize
		if(self.postTestMergeComment is not None): _dict["postTestMergeComment"] = self.postTestMergeComment
		if(self.updateSubmodules is not None): _dict["updateSubmodules"] = self.updateSubmodules
		if(self.newTestMerges is not None):
			tmList = list()
			for tm in self.newTestMerges:
				tmList.append(tm.encode((dict())))
			_dict["updateSubmodules"] = tmList
		return _dict

def make_request(address: str, method = "get", headers = None, json = None) -> requests.Response:
	_headers = {"User-Agent": "TGSLink/1.0"}
	for header in headers.keys():
		_headers[header] = headers[header]
	ssl_context = [None, ssl.create_default_context()][address.startswith("https://")]
	return requests.request(method, address, headers=_headers, json=json)

def tgs_request(address, path = "/", method = "get", token = None, json = None, headers: 'dict[str,str]' = None):
	_headers = {"Api": "Tgstation.Server.Api/9.3.0", "User-Agent": "TGSLink/1.0", "accept": "application/json"}
	if(token): _headers["Authorization"] = "Bearer {}".format(token)
	if(headers is not None):
		for key in headers.keys():
			_headers[key] = headers[key]
	return make_request("{}{}".format(address, path), method, _headers, json)

def tgs_server_info(address, token):
	return tgs_request(address, "/Administration", token=token)

def tgs_login(address, username, password) -> Tuple[Tuple[str, float], None]:
	basic = base64.b64encode("{}:{}".format(username, password).encode("ascii")).decode("ascii")
	resp = tgs_request(address, method="post", headers={"Authorization": "Basic {}".format(basic)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	resp = resp.json()
	expStr = resp["expiresAt"].split(".")[0]
	return tuple([resp["bearer"], datetime.strptime(expStr, "%Y-%m-%dT%H:%M:%S").timestamp()])

def tgs_instances(address, token) -> Tuple[InstanceInformationQuery, None]:
	resp = tgs_request(address, "/Instance/List", token=token)
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=InstanceInformationQuery)

def tgs_get_instance(address, token, instance) -> Tuple[InstanceInformation, None]:
	resp = tgs_request(address, "/Instance/{}".format(instance), token=token)
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=InstanceInformation)

def tgs_dm_deploy(address, token, instance) -> Tuple[JobInformation, None]:
	resp = tgs_request(address, "/DreamMaker", method="put", token=token, headers={"Instance": "{}".format(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformation)

def tgs_job_get(address, token, instance, jobid) -> Tuple[JobInformation, None]:
	resp = tgs_request(address, "/Job/{}".format(jobid), token=token, headers={"Instance": "{}".format(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformation)

def tgs_job_all(address, token, instance) -> Tuple[JobInformationQuery, None]:
	resp = tgs_request(address, "/Job/List", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformationQuery)

def tgs_watchdog_status(address, token, instance) -> Tuple[WatchdogStatus, None]:
	resp = tgs_request(address, "/DreamDaemon", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=WatchdogStatus)

def tgs_watchdog_start(address, token, instance) -> Tuple[JobInformation, None]:
	resp = tgs_request(address, "/DreamDaemon", method="put", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=JobInformation)

def tgs_watchdog_shutdown(address, token, instance) -> Tuple[bool, None]:
	resp = tgs_request(address, "/DreamDaemon", method="delete", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.status_code == 204

def tgs_repo_status(address, token, instance) -> Tuple[RepositoryStatus, None]:
	resp = tgs_request(address, "/Repository", token=token, headers={"Instance": str(instance)})
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=RepositoryStatus)

def tgs_repo_update_tms(address, token, instance, gh_token, update_from_origin=True) -> Tuple[bool, None]:
	log.info("getting status")
	status: RepositoryStatus = tgs_repo_status(address, token, instance)
	if(not status): return None

	log.info("assembling tms")
	new_tms: list[TestMergeParamaters] = list()
	for tm in status.revisionInformation.activeTestMerges:
		sleep(0.2)
		gh_pr: GHPullRequest = gh_get_pr(status.remoteRepositoryOwner, status.remoteRepositoryName, tm.number, gh_token)
		if(not gh_pr): return None

		if(gh_pr.is_closed() and update_from_origin): continue
		new_tms.append(TestMergeParamaters().decode({"number": tm.number, "comment": "automatic update", "targetCommitSha": gh_pr.head.sha}))
	
	log.info("{} tms to update, {} to remove".format(len(new_tms), len(status.revisionInformation.activeTestMerges) - len(new_tms)))
	if(len(new_tms) == 0): new_tms = None
	update_req: RepositoryUpdateRequest = RepositoryUpdateRequest()
	update_req.updateFromOrigin = update_from_origin
	update_req.newTestMerges = new_tms

	log.info("Sending request: {}".format(update_req.encode(dict())))
	resp = tgs_request(address, "/Repository", method="post", token=token, json=JSONEncoder().encode(update_req.encode(dict())))
	if(not resp):
		log.info(resp)
		return None
	resp: RepositoryStatus = resp.json(cls=RepositoryStatus)

	job: JobInformation = resp.activeJob

	log.info("Waiting for job completion")
	wait_count = 0
	while not job.stoppedAt:
		if(wait_count > 10): return None
		wait_count += 1
		sleep(2)
		job = tgs_job_get(address, token, instance, job.id)

	if(job.errorCode):
		log.info(job.exceptionDetails)
		return None
	return True

class GHHead:
	label: str
	ref: str
	sha: str

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		self.label = dict["label"]
		self.ref = dict["ref"]
		self.sha = dict["sha"]
		return self

class GHPullRequest:
	url: str
	number: int
	state: str
	locked: bool
	title: str
	head: GHHead

	def decode(self, dict):
		if(isinstance(dict, str)):
			dict = JSONDecoder().decode(dict)
		if("url" in dict.keys()): self.url = dict["url"]
		if("number" in dict.keys()): self.number = dict["number"]
		if("state" in dict.keys()): self.state = dict["state"]
		if("locked" in dict.keys()): self.locked = dict["locked"]
		if("title" in dict.keys()): self.title = dict["title"]
		if("head" in dict.keys()): self.head = GHHead().decode(dict["head"])
		return self
	
	def is_closed(self):
		return self.state != "open"

def gh_get_pr(repo_owner, repo_name, pr_id, token) -> Tuple[GHPullRequest, None]:
	auth_header = {"Authorization": "token {}".format(token)}
	resp = make_request("https://api.github.com/repos/{}/{}/pulls/{}".format(repo_owner, repo_name, pr_id), headers=auth_header)
	if(resp is None):
		return None
	if(not resp.ok):
		log.info("Failed to run query: {}".format(resp.reason))
		return None
	return resp.json(cls=GHPullRequest)
