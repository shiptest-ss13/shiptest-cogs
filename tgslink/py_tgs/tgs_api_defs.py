from argparse import ArgumentError
import base64
from codecs import ascii_encode
import logging
from time import sleep
from typing import Iterator, List
import requests
import github

from .tgs_api_models import JobState, PythonTgsApi, TgsModel_AdministrationResponse, TgsModel_ByondInstallResponse, TgsModel_ByondResponse, TgsModel_ByondVersionRequest, TgsModel_CompileJobResponse, TgsModel_DreamDaemonResponse, TgsModel_DreamMakerRequest, TgsModel_DreamMakerResponse, TgsModel_ErrorMessageResponse, TgsModel_Instance, TgsModel_JobResponse, TgsModel_LogFileResponse, TgsModel_PaginatedResponse, TgsModel_RepositoryCreateRequest, TgsModel_RepositoryResponse, TgsModel_RepositoryUpdateRequest, TgsModel_ServerUpdateRequest, TgsModel_ServerUpdateResponse, TgsModel_TestMergeParameters, TgsModel_TokenResponse, TgsModelBase
log = logging.getLogger("red.pytgs")


def __query(page, page_size):
    return {"page": page, "pageSize": page_size}


def __tgs_request(address, path="/", *, cls, method="get", token=None, json=None, data=None, headers: 'dict[str,str]' = None, query: 'dict[str, str]' = None) -> object:
    if cls is None:
        raise ArgumentError()
    pyTgs = PythonTgsApi()
    _headers = {"Api": "Tgstation.Server.Api/{}".format(pyTgs.ApiVersion), "User-Agent": pyTgs.UserAgent, "accept": "application/json"}
    if token:
        _headers["Authorization"] = "Bearer {}".format(token)
    if headers is not None:
        for key in headers.keys():
            _headers[key] = headers[key]
    if data is not None and json is not None:
        raise ArgumentError("Conflicting parameters, cannot supply both data and json")
    _data = data
    if json is not None:
        _headers["Content-Type"] = "application/json"
        _data = ascii_encode(json)[0]
    req = requests.request(method, "{}{}".format(address, path), headers=_headers, data=_data, params=query)
    if req is None:
        raise IOError()
    if not req.ok:
        if len(req.content):
            err: TgsModel_ErrorMessageResponse = req.json(cls=TgsModel_ErrorMessageResponse)
        else:
            err = TgsModel_ErrorMessageResponse()
        err._status_code = req.status_code
        if not err.Message:
            err.sanitize()
        raise err
    if cls == int:
        return req.status_code
    if cls == bytes:
        return req.content
    if cls == TgsModel_TokenResponse and req.status_code == 401:
        raise IOError("Unauthorized")
    if issubclass(cls, TgsModelBase):
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


# administration routes #


def tgs_server_status(address, token) -> TgsModel_AdministrationResponse:
    return __tgs_request(address, "/Administration", token=token, cls=TgsModel_AdministrationResponse)


def tgs_server_update(address, token, request: TgsModel_ServerUpdateRequest) -> TgsModel_ServerUpdateResponse:
    return __tgs_request(address, "/Administration", method="post", token=token, json=request.encode(), cls=TgsModel_ServerUpdateResponse)


def tgs_server_restart(address, token) -> bool:
    return __tgs_request(address, "/Administration", method="delete", token=token, cls=int) == 204


def tgs_server_logs(address, token, page=1, page_size=25) -> List[TgsModel_LogFileResponse]:
    resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Administration/Logs", token=token, cls=TgsModel_PaginatedResponse, query=__query(page, page_size))
    return resp.iter_as(TgsModel_LogFileResponse)


def tgs_server_log_download(address, token, log_instance: TgsModel_LogFileResponse):
    ticket: TgsModel_LogFileResponse = __tgs_request(address, "/Administration/Logs/{}".format(log_instance.Name), token=token, cls=TgsModel_LogFileResponse)
    transf = tgs_transfer_download(address, token, ticket.FileTicket)
    return transf


# byond routes #


def tgs_byond_list(address, token, instance, page=1, page_size=25) -> Iterator[TgsModel_ByondResponse]:
    resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Byond/List", token=token, cls=TgsModel_PaginatedResponse, headers={"Instance": str(instance)}, query=__query(page, page_size))
    return resp.iter_as(TgsModel_ByondResponse)


def tgs_byond_set_active(address, token, instance, byond: TgsModel_ByondVersionRequest) -> TgsModel_ByondInstallResponse:
    resp: TgsModel_ByondInstallResponse = __tgs_request(address, "/Byond", method="post", token=token, headers={"Instance": str(instance)}, cls=TgsModel_ByondInstallResponse, json=byond.encode())
    if isinstance(resp, int):
        raise IOError()

    if resp.InstallJob:
        target_id = resp.InstallJob.Id
        refresh = tgs_job_get(address, token, instance, target_id)
        while not refresh.StoppedAt:
            sleep(0.5)
            refresh = tgs_job_get(address, token, instance, target_id)

        if refresh.ErrorCode:
            failure = TgsModel_ErrorMessageResponse()
            failure.ErrorCode = failure.errno = refresh.ErrorCode
            failure.Message = refresh.ExceptionDetails
            raise failure

        return refresh

    return resp


def tgs_byond_get_active(address, token, instance) -> TgsModel_ByondResponse:
    return __tgs_request(address, "/Byond", token=token, cls=TgsModel_ByondResponse, headers={"Instance": str(instance)})


# chat routes # TODO


# configuration routes # TODO


# dream daemon routes #


def tgs_dd_launch(address, token, instance=1) -> bool:
    resp: TgsModel_JobResponse = __tgs_request(address, "/DreamDaemon", headers={"Instance": str(instance)}, method="put", token=token, cls=TgsModel_JobResponse)
    while not resp.StoppedAt:
        sleep(0.5)
        resp = tgs_job_get(address, token, instance, resp.Id)
    return resp.ok()


def tgs_dd_stop(address, token, instance=1) -> bool:
    resp: TgsModel_JobResponse = __tgs_request(address, "/DreamDaemon", headers={"Instance": str(instance)}, method="delete", token=token, cls=TgsModel_JobResponse)
    while not resp.StoppedAt:
        sleep(0.5)
        resp = tgs_job_get(address, token, instance, resp.Id)
    return resp.ok()


def tgs_dd_restart(address, token, instance=1) -> TgsModel_JobResponse:
    return __tgs_request(address, "/DreamDaemon", headers={"Instance": str(instance)}, method="patch", token=token, cls=TgsModel_JobResponse)


def tgs_dd_status(address, token, instance=1) -> TgsModel_DreamDaemonResponse:
    return __tgs_request(address, "/DreamDaemon", headers={"Instance": str(instance)}, token=token, cls=TgsModel_DreamDaemonResponse)


def tgs_dd_update(address, token, req: TgsModel_DreamDaemonResponse, instance=1) -> TgsModel_DreamDaemonResponse:
    return __tgs_request(address, "/DreamDaemon", headers={"Instance": str(instance)}, method="post", token=token, cls=TgsModel_DreamDaemonResponse, json=req.encode())


# dream maker routes #


def tgs_dm_status(address, token, instance) -> TgsModel_DreamMakerResponse:
    return __tgs_request(address, "/DreamMaker", headers={"Instance": str(instance)}, token=token, cls=TgsModel_DreamMakerResponse)


def tgs_dm_compile_job(address, token, instance, job_id) -> TgsModel_CompileJobResponse:
    return __tgs_request(address, "/DreamMaker/{}".format(job_id), headers={"Instance": str(instance)}, token=token, cls=TgsModel_CompileJobResponse)


def tgs_dm_compile_job_list(address, token, instance, page=1, page_size=25) -> List[TgsModel_CompileJobResponse]:
    resp: TgsModel_PaginatedResponse = __tgs_request(address, "/DreamMaker/List", headers={"Instance": str(instance)}, token=token, query=__query(page, page_size), cls=TgsModel_PaginatedResponse)
    return resp.iter_as(TgsModel_CompileJobResponse)


def tgs_dm_compile_job_list_all(address, token, instance) -> List[TgsModel_CompileJobResponse]:
    first = tgs_dm_compile_job_list(address, token, instance, 1, 1)[0]
    return tgs_dm_compile_job_list(address, token, instance, 1, first.Id)


def tgs_dm_deploy(address, token, instance) -> TgsModel_JobResponse:
    return __tgs_request(address, "/DreamMaker", method="put", headers={"Instance": str(instance)}, token=token, cls=TgsModel_JobResponse)


def tgs_dm_update(address, token, instance, req: TgsModel_DreamMakerRequest) -> TgsModel_DreamMakerResponse:
    return __tgs_request(address, "/DreamMaker", method="post", headers={"Instance": str(instance)}, token=token, cls=TgsModel_DreamMakerResponse, json=req.encode())

# instance routes # TODO

# instance permission routes # TODO

# job routes #


def tgs_job_list(address, token, instance, page=1, page_size=25) -> List[TgsModel_JobResponse]:
    resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Job", headers={"Instance": str(instance)}, token=token, query=__query(page, page_size), cls=TgsModel_PaginatedResponse)
    for entry in resp.Content:
        yield TgsModel_JobResponse().from_dict(entry)


def tgs_job_all(address, token, instance, page=1, page_size=25) -> List[TgsModel_JobResponse]:
    resp: TgsModel_PaginatedResponse = __tgs_request(address, "/Job/List", headers={"Instance": str(instance)}, token=token, query=__query(page, page_size), cls=TgsModel_PaginatedResponse)
    for entry in resp.Content:
        yield TgsModel_JobResponse().from_dict(entry)


def tgs_job_cancel(address, token, instance, job_id) -> TgsModel_JobResponse:
    req: TgsModel_JobResponse = __tgs_request(address, "/Job/{}".format(job_id), method="delete", headers={"Instance": str(instance)}, token=token, cls=TgsModel_JobResponse)
    while req.state() == JobState.Running:
        sleep(0.5)
        req = tgs_job_get(address, token, instance, job_id)
    return req


def tgs_job_get(address, token, instance, job_id) -> TgsModel_JobResponse:
    return __tgs_request(address, "/Job/{}".format(job_id), headers={"Instance": str(instance)}, token=token, cls=TgsModel_JobResponse)

# repository routes #


def tgs_repo_clone(address, token, instance, req: TgsModel_RepositoryCreateRequest) -> TgsModel_RepositoryResponse:
    return __tgs_request(address, "/Repository", method="put", headers={"Instance": str(instance)}, token=token, cls=TgsModel_RepositoryResponse, json=req.encode())


def tgs_repo_delete(address, token, instance) -> TgsModel_RepositoryResponse:
    return __tgs_request(address, "/Repository", method="delete", headers={"Instance": str(instance)}, token=token, cls=TgsModel_RepositoryResponse)


def tgs_repo_status(address, token, instance) -> TgsModel_RepositoryResponse:
    return __tgs_request(address, "/Repository", headers={"Instance": str(instance)}, token=token, cls=TgsModel_RepositoryResponse)


def tgs_repo_update(address, token, instance, req: TgsModel_RepositoryUpdateRequest) -> TgsModel_RepositoryResponse:
    return __tgs_request(address, "/Repository", method="post", headers={"Instance": str(instance)}, token=token, cls=TgsModel_RepositoryResponse, json=req.encode())


def tgs_repo_update_tms(address, token, instance):
    current = tgs_repo_status(address, token, instance)
    gh = github.Github()
    gh_repo = gh.get_repo("{}/{}".format(current.RemoteRepositoryOwner, current.RemoteRepositoryName))

    new_tms = list()
    any_changes = False
    for tm in current.RevisionInformation.ActiveTestMerges:
        tm_pr = gh_repo.get_pull(tm.Number)
        if tm_pr.closed_at is not None:
            continue
        if tm_pr.head.sha != tm.TargetCommitSha:
            any_changes = True
        _tm = TgsModel_TestMergeParameters()
        _tm.Number = tm.Number
        new_tms.append(_tm)

    if not len(new_tms) or not any_changes:
        return True
    req = TgsModel_RepositoryUpdateRequest()
    req.NewTestMerges = new_tms
    req.UpdateFromOrigin = True
    req.Reference = current.Reference
    resp = tgs_repo_update(address, token, instance, req)
    job = resp.ActiveJob
    if job is None:
        return False
    while not job.StoppedAt:
        sleep(0.5)
        job = tgs_job_get(address, token, instance, job.Id)
    return job.ok()

# swarm routes # TODO


# transfer routes #


def tgs_transfer_download(address, token, ticket) -> bytes:
    return __tgs_request(address, "/Transfer", token=token, query={"ticket": ticket}, headers={"Accept": "application/octet-stream, application/json"}, cls=bytes)


def tgs_transfer_upload(address, token, ticket, content: bytes) -> bool:
    return __tgs_request(address, "/Transfer", token=token, query={"ticket": ticket}, cls=int) == 204

# user routes # TODO

# user group routes # TODO
