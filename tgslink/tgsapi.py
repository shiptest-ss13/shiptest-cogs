from audioop import add
import base64
from datetime import datetime
from json import JSONDecoder, JSONEncoder
from logging import error
import ssl
from time import sleep
import requests
from typing import Dict, Tuple

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
	return make_request("http://{}{}".format(address, path), method, _headers, json)

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
	return tuple([resp["bearer"], resp["expiresAt"]])

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
