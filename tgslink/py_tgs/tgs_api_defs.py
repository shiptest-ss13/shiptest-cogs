from argparse import ArgumentError
import base64
from codecs import ascii_encode
from http.client import UNAUTHORIZED
import logging
from time import sleep
from typing import List
from urllib.error import HTTPError
from requests import request

from .tgs_api_models import *
log = logging.getLogger("PyTgs")

def __tgs_request(address, path = "/", *, cls, method = "get", token = None, json = None, data = None, headers: 'dict[str,str]' = None, query: 'dict[str, str]'= None) -> object:
	if(cls is None): raise ArgumentError()
	pyTgs = PythonTgsApi()
	_headers = {"Api": "Tgstation.Server.Api/{}".format(pyTgs.ApiVersion), "User-Agent": pyTgs.UserAgent, "accept": "application/json"}
	if(token): _headers["Authorization"] = "Bearer {}".format(token)
	if(headers is not None):
		for key in headers.keys():
			_headers[key] = headers[key]
	if(data is not None and json is not None): raise ArgumentError("Conflicting parameters, cannot supply both data and json")
	_data = data
	if(json is not None):
		_headers["Content-Type"] = "application/json"
		_data = ascii_encode(json)[0]
	req = request(method, "{}{}".format(address, path), headers=_headers, data=_data, params=query)
	if(req is None): raise IOError()
	if(not req.ok):
		err: TgsModel_ErrorMessageResponse = req.json(cls=TgsModel_ErrorMessageResponse)
		err._status_code = req.status_code
	if(cls == int): return req.status_code
	if(cls == bytes): return req.content
	if(cls == TgsModel_TokenResponse and req.status_code == 401):
		raise IOError("Unauthorized")
	if(issubclass(cls, TgsModelBase)):
		ret: TgsModelBase = req.json(cls=cls)
		ret._status_code = req.status_code
		return ret
	raise ArgumentError("I dont know how to process {}".format(cls))

def tgs_login(address, username, password) -> TgsModel_TokenResponse:
	basic = base64.b64encode("{}:{}".format(username, password).encode("ascii")).decode("ascii")
	return __tgs_request(address, cls=TgsModel_TokenResponse, method="post", headers={"Authorization": "Basic {}".format(basic)})

def tgs_instances(address, token) -> Iterator[TgsModel_Instance]:
	resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Instance/List", token=token, cls=TgsModel_PaginatedResponse)
	for dict in resp.Content:
		yield TgsModel_Instance().from_dict(dict)

def tgs_instance(address, token, instance) -> TgsModel_Instance:
	return __tgs_request(address, "/Instance/{}".format(instance), token=token, cls=TgsModel_Instance)

def tgs_watchdog_status(address, token, instance) -> TgsModel_DreamDaemonResponse:
	return __tgs_request(address, "/DreamDaemon", token=token, cls=TgsModel_DreamDaemonResponse, headers={"Instance": str(instance)})

## administration routes ##

def tgs_server_status(address, token) -> TgsModel_AdministrationResponse:
	return __tgs_request(address, "/Administration", token=token, cls=TgsModel_AdministrationResponse)

def tgs_server_update(address, token, request: TgsModel_ServerUpdateRequest) -> TgsModel_ServerUpdateResponse:
	return __tgs_request(address, "/Administration", method="post", token=token, json=request.encode(), cls=TgsModel_ServerUpdateResponse)

def tgs_server_restart(address, token) -> bool:
	return __tgs_request(address, "/Administration", method="delete", token=token, cls=int) == 204

def tgs_server_logs(address, token, page=1, page_size=25) -> 'list[TgsModel_LogFileResponse]':
	resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Administration/Logs", token=token, cls=TgsModel_PaginatedResponse, query={"page": str(page), "pageSize":str(page_size)})
	return resp.iter_as(TgsModel_LogFileResponse)

def tgs_server_log_download(address, token, log_instance: TgsModel_LogFileResponse):
	ticket: TgsModel_LogFileResponse = __tgs_request(address, "/Administration/Logs/{}".format(log_instance.Name), token=token, cls=TgsModel_LogFileResponse)
	transf = tgs_transfer_download(address, token, ticket.FileTicket)
	return transf

## byond routes ##

def tgs_byond_list(address, token, instance, page=1, page_size=25) -> Iterator[TgsModel_ByondResponse]:
	resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Byond/List", token=token, cls=TgsModel_PaginatedResponse, headers={"Instance": str(instance)}, query={"page": page, "pageSize": page_size})
	for dict in resp.Content: yield TgsModel_ByondResponse().from_dict(dict)

def tgs_byond_set_active(address, token, instance, byond: TgsModel_ByondVersionRequest) -> TgsModel_ByondInstallResponse:
	resp: TgsModel_ByondInstallResponse = __tgs_request(address, "/Byond", method="post", token=token, headers={"Instance": str(instance)}, cls=TgsModel_ByondInstallResponse, json=byond.encode())
	if(isinstance(resp, int)): raise IOError()

	if(resp.InstallJob):
		target_id = resp.InstallJob.Id
		refresh = tgs_job_get(address, token, instance, target_id)
		while(not refresh.StoppedAt):
			sleep(0.5)
			refresh = tgs_job_get(address, token, instance, target_id)

		if(refresh.ErrorCode):
			failure = TgsModel_ErrorMessageResponse()
			failure.ErrorCode = failure.errno = refresh.ErrorCode
			failure.Message = refresh.ExceptionDetails
			raise failure

		return refresh

	return resp

def tgs_byond_get_active(address, token, instance) -> TgsModel_ByondResponse:
	return __tgs_request(address, "/Byond", token=token, cls=TgsModel_ByondResponse, headers={"Instance": str(instance)})

## chat routes ## TODO

## configuration routes ## TODO

## dream daemon routes ## TODO

## dream maker routes ## TODO

## instance routes ## TODO

## instance permission routes ## TODO

## job routes ##

def tgs_job_list(address, token, instance, page=1, page_size=25) -> List[TgsModel_JobResponse]:
	resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Job", headers={"Instance": str(instance)}, token=token, query={"page": page, "pageSize": page_size}, cls=TgsModel_PaginatedResponse)
	for entry in resp.Content:
		yield TgsModel_JobResponse().from_dict(entry)

def tgs_job_all(address, token, instance, page=1, page_size=25) -> List[TgsModel_JobResponse]:
	resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Job/List", headers={"Instance": str(instance)}, token=token, query={"page": page, "pageSize": page_size}, cls=TgsModel_PaginatedResponse)
	for entry in resp.Content:
		yield TgsModel_JobResponse().from_dict(entry)

def tgs_job_cancel(address, token, instance, job_id) -> TgsModel_JobResponse:
	return __tgs_request(address, "/Job/{}".format(job_id), method="delete", headers={"Instance": str(instance)}, token=token, cls=TgsModel_JobResponse)

def tgs_job_get(address, token, instance, job_id) -> TgsModel_JobResponse:
	return __tgs_request(address, "/Job/{}".format(job_id), headers={"Instance": str(instance)}, token=token, cls=TgsModel_JobResponse)

## repository routes ## TODO

## swarm routes ## TODO

## transfer routes ##

def tgs_transfer_download(address, token, ticket) -> bytes:
	return __tgs_request(address, "/Transfer", token=token, query={"ticket": ticket}, headers={"Accept": "application/octet-stream, application/json"}, cls=bytes)

def tgs_transfer_upload(address, token, ticket, content: bytes) -> bool:
	return __tgs_request(address, "/Transfer", token=token, query={"ticket": ticket}, cls=int) == 204

## user routes ## TODO

## user group routes ## TODO
