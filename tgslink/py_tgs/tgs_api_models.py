from datetime import datetime, timedelta
from enum import Enum, Flag
from inspect import ismethod
from json import JSONDecoder, JSONEncoder
import json
import logging
from operator import contains
from typing import Iterable, Iterator
from uuid import UUID

log = logging.getLogger("PyTgsModels")

class PythonTgsApi:
	ApiVersion = "9.3.0"
	UserAgent = "PyTgs/1.0"

def tgs_datetime(str) -> datetime:
	return datetime.strptime(str.split(".")[0], "%Y-%m-%dT%H:%M:%S")

class TgsModelBase:
	_base_json: str = None
	_status_code: int = None

	def decode(self, json):
		self._base_json = json
		if(not json): raise IOError()
		return self.from_dict(JSONDecoder().decode(json))

	def from_dict(self, dict):
		log.info("decoding {}:".format(self.__class__.__name__))
		_dict_keys = dict.keys()

		for key in dir(self):
			if(key.startswith("_")): continue
			j_key = key[0].lower() + key[1:]
			if(contains(_dict_keys, j_key)):
				setattr(self, key, dict[j_key])
				log.info(" -- {}".format(key))
		self.sanitize()
		if(not self._base_json): self._base_json = JSONEncoder().encode(dict)
		return self

	def sanitize(self):
		"""
		Ensure that all variables set during decode are valid
		"""
		log.info("sanitizing {}".format(self.__class__.__name__))

	def encode(self):
		log.info("encoding {}:".format(self.__class__.__name__))
		_dict: dict = dict()
		for key in dir(self):
			if(key.startswith("_")): continue
			# j_key = key[0].lower() + key[1:]
			val = getattr(self, key)
			if(ismethod(val)): continue
			log.info(" -- {}".format(key))
			_dict[key] = val

		return json.dumps(_dict, sort_keys=True, indent=None)
	
	def __str__(self) -> str:
		return "{}|{}".format(self.__class__.__name__, self._base_json)

	def __bool__(self) -> bool:
		return self._status_code < 400
	
	def ok(self) -> bool: self.__bool__()

class TgsModel_EntityId(TgsModelBase):
	Id: int = None

class TgsModel_NamedEntity(TgsModel_EntityId):
	Name: str = None

class TgsModel_UserName(TgsModel_NamedEntity):
	pass

class TgsModel_UserModelBase(TgsModel_UserName):
	Enabled: bool = None
	CreatedAt: datetime = None
	SystemIdentifier: str = None

	def sanitize(self):
		super().sanitize()
		self.CreatedAt = tgs_datetime(self.CreatedAt)

class TgsModel_AdministrationRights(Flag):
	WriteUsers = 1
	RestartHost = 2
	ChangeVersion = 4
	EditOwnPassword = 8
	ReadUsers = 16
	DownloadLogs = 32
	EditOwnOAuthConnections = 64

class TgsModel_InstanceManagerRights(Flag):
	Read = 1
	Create = 2
	Rename = 4
	Relocate = 8
	SetOnline = 16
	Delete = 32
	List = 64
	SetConfiguration = 128
	SetAutoUpdate = 256
	SetChatBotLimit = 512
	GrantPermissions = 1024

class TgsModel_PermissionSet(TgsModel_EntityId):
	AdministrationRights: TgsModel_AdministrationRights = None
	InstanceManagerRights: TgsModel_InstanceManagerRights = None

class TgsModel_OAuthProvider(Enum):
	GitHub = "GitHub"
	Discord = "Discord"
	TGForums = "TGForums"
	Keycloak = "Keycloak"
	InvisionCommunity = "InvisionCommunity"

class TgsModel_OAuthConnection(TgsModelBase):
	Provider: TgsModel_OAuthProvider = None
	ExternalUserId: str = None

class TgsModel_UserGroup(TgsModel_NamedEntity):
	PermissionSet: TgsModel_PermissionSet = None

	def sanitize(self):
		super().sanitize()
		self.PermissionSet = TgsModel_PermissionSet().from_dict(self.PermissionSet)

class TgsModel_UserApiBase(TgsModel_UserModelBase):
	OAuthConnections: 'list[TgsModel_OAuthConnection]' = None
	PermissionSet: TgsModel_PermissionSet = None
	Group: TgsModel_UserGroup = None

	def sanitize(self):
		super().sanitize()
		_l = list()
		for oauth in self.OAuthConnections: _l.append(TgsModel_OAuthConnection().from_dict(oauth))
		self.OAuthConnections = _l
		self.PermissionSet = TgsModel_PermissionSet().from_dict(self.PermissionSet)
		self.Group = TgsModel_UserGroup().from_dict(self.Group)

class TgsModel_UserResponse(TgsModel_UserApiBase):
	CreatedBy: TgsModel_UserName = None

	def sanitize(self):
		super().sanitize()
		self.CreatedBy = TgsModel_UserName().from_dict(self.CreatedBy)

class TgsModel_AdministrationResponse(TgsModelBase):
	TrackedRepositoryUrl: str = None
	LatestVersion: str = None

class TgsModel_FileTicketResponse(TgsModelBase):
	FileTicket: str = None

class TgsModel_RightsType(Enum):
	Administration = 0
	InstanceManager = 1
	Repository = 2
	Byond = 3
	DreamMaker = 4
	DreamDaemon = 5
	ChatBots = 6
	Configuration = 7
	InstancePermissionSet = 8

class TgsModel_ErrorCode(Enum):
	InternalServerError = "InternalServerError"
	ApiMismatch = "ApiMismatch"
	ModelValidationFailure = "ModelValidationFailure"
	IOError = "IOError"
	BadHeaders = "BadHeaders"
	TokenWithToken = "TokenWithToken"
	DatabaseIntegrityConflict = "DatabaseIntegrityConflict"
	MissingHostWatchdog = "MissingHostWatchdog"
	CannotChangeServerSuite = "CannotChangeServerSuite"
	RemoteApiError = "RemoteApiError"
	ServerUpdateInProgress = "ServerUpdateInProgress"
	UserNameChange = "UserNameChange"
	UserSidChange = "UserSidChange"
	UserMismatchNameSid = "UserMismatchNameSid"
	UserMismatchPasswordSid = "UserMismatchPasswordSid"
	UserPasswordLength = "UserPasswordLength"
	UserColonInName = "UserColonInName"
	UserMissingName = "UserMissingName"
	InstanceRelocateOnline = "InstanceRelocateOnline"
	InstanceAtExistingPath = "InstanceAtExistingPath"
	InstanceDetachOnline = "InstanceDetachOnline"
	InstanceAtConflictingPath = "InstanceAtConflictingPath"
	InstanceLimitReached = "InstanceLimitReached"
	InstanceWhitespaceName = "InstanceWhitespaceName"
	InstanceHeaderRequired = "InstanceHeaderRequired"
	RequiresPosixSystemIdentity = "RequiresPosixSystemIdentity"
	ConfigurationFileUpdated = "ConfigurationFileUpdated"
	ConfigurationDirectoryNotEmpty = "ConfigurationDirectoryNotEmpty"
	UnusedErrorCode1 = "UnusedErrorCode1"
	RepoMismatchUserAndAccessToken = "RepoMismatchUserAndAccessToken"
	RepoCloning = "RepoCloning"
	RepoBusy = "RepoBusy"
	RepoExists = "RepoExists"
	RepoMissing = "RepoMissing"
	RepoMismatchShaAndReference = "RepoMismatchShaAndReference"
	RepoMismatchShaAndUpdate = "RepoMismatchShaAndUpdate"
	UnusedErrorCode2 = "UnusedErrorCode2"
	RepoDuplicateTestMerge = "RepoDuplicateTestMerge"
	RepoWhitespaceCommitterName = "RepoWhitespaceCommitterName"
	RepoWhitespaceCommitterEmail = "RepoWhitespaceCommitterEmail"
	ApiPageTooLarge = "ApiPageTooLarge"
	ApiInvalidPageOrPageSize = "ApiInvalidPageOrPageSize"
	ChatBotWrongChannelType = "ChatBotWrongChannelType"
	ChatBotWhitespaceConnectionString = "ChatBotWhitespaceConnectionString"
	ChatBotWhitespaceName = "ChatBotWhitespaceName"
	ChatBotProviderMissing = "ChatBotProviderMissing"
	UnusedErrorCode3 = "UnusedErrorCode3"
	ChatBotMax = "ChatBotMax"
	ChatBotMaxChannels = "ChatBotMaxChannels"
	ByondDirectXInstallFail = "ByondDirectXInstallFail"
	ByondDownloadFail = "ByondDownloadFail"
	ByondNoVersionsInstalled = "ByondNoVersionsInstalled"
	DreamMakerNeverValidated = "DreamMakerNeverValidated"
	DreamMakerInvalidValidation = "DreamMakerInvalidValidation"
	CannotRemoveLastAuthenticationOption = "CannotRemoveLastAuthenticationOption"
	DreamMakerNoDme = "DreamMakerNoDme"
	DreamMakerMissingDme = "DreamMakerMissingDme"
	DreamMakerExitCode = "DreamMakerExitCode"
	DreamMakerCompileJobInProgress = "DreamMakerCompileJobInProgress"
	InstanceMissingDreamDaemonSettings = "InstanceMissingDreamDaemonSettings"
	InstanceMissingDreamMakerSettings = "InstanceMissingDreamMakerSettings"
	InstanceMissingRepositorySettings = "InstanceMissingRepositorySettings"
	InstanceUpdateTestMergeConflict = "InstanceUpdateTestMergeConflict"
	RepoCredentialsRequired = "RepoCredentialsRequired"
	RepoCannotAuthenticate = "RepoCannotAuthenticate"
	RepoReferenceRequired = "RepoReferenceRequired"
	WatchdogRunning = "WatchdogRunning"
	WatchdogCompileJobCorrupted = "WatchdogCompileJobCorrupted"
	WatchdogStartupFailed = "WatchdogStartupFailed"
	WatchdogStartupTimeout = "WatchdogStartupTimeout"
	RepoUnsupportedTestMergeRemote = "RepoUnsupportedTestMergeRemote"
	RepoSwappedShaOrReference = "RepoSwappedShaOrReference"
	RepoMergeConflict = "RepoMergeConflict"
	RepoReferenceNotTracking = "RepoReferenceNotTracking"
	RepoTestMergeConflict = "RepoTestMergeConflict"
	InstanceNotAtWhitelistedPath = "InstanceNotAtWhitelistedPath"
	DreamDaemonDoubleSoft = "DreamDaemonDoubleSoft"
	DeploymentPagerRunning = "DeploymentPagerRunning"
	DreamDaemonPortInUse = "DreamDaemonPortInUse"
	PostDeployFailure = "PostDeployFailure"
	WatchdogNotRunning = "WatchdogNotRunning"
	ResourceNotPresent = "ResourceNotPresent"
	ResourceNeverPresent = "ResourceNeverPresent"
	GitHubApiRateLimit = "GitHubApiRateLimit"
	JobStopped = "JobStopped"
	MissingGCore = "MissingGCore"
	GCoreFailure = "GCoreFailure"
	RepoTestMergeInvalidRemote = "RepoTestMergeInvalidRemote"
	ByondNonExistentCustomVersion = "ByondNonExistentCustomVersion"
	DreamDaemonOffline = "DreamDaemonOffline"
	InstanceOffline = "InstanceOffline"
	ChatCannotConnectProvider = "ChatCannotConnectProvider"
	ByondDreamDaemonFirewallFail = "ByondDreamDaemonFirewallFail"
	NoPortsAvailable = "NoPortsAvailable"
	PortNotAvailable = "PortNotAvailable"
	AdminUserCannotOAuth = "AdminUserCannotOAuth"
	OAuthProviderDisabled = "OAuthProviderDisabled"
	FileUploadExpired = "FileUploadExpired"
	UserGroupAndPermissionSet = "UserGroupAndPermissionSet"
	UserGroupNotEmpty = "UserGroupNotEmpty"
	UserLimitReached = "UserLimitReached"
	UserGroupLimitReached = "UserGroupLimitReached"
	DeploymentTimeout = "DeploymentTimeout"

class TgsModel_Job(TgsModel_EntityId):
	Description: str = None
	ErrorCode: TgsModel_ErrorCode = None
	ExceptionDetails: str = None
	StartedAt: datetime = None
	StoppedAt: datetime = None
	Cancelled: bool = None
	CancelRightsType: TgsModel_RightsType = None
	CancelRight: int = None

	def sanitize(self):
		super().sanitize()
		self.StartedAt = tgs_datetime(self.StartedAt)
		if(self.StoppedAt): self.StoppedAt = tgs_datetime(self.StoppedAt)

class TgsModel_JobResponse(TgsModel_Job):
	StartedBy: TgsModel_UserName = None
	CancelledBy: TgsModel_UserName = None
	Progress: int = None
	Stage: str = None

	def sanitize(self):
		super().sanitize()
		self.StartedBy = TgsModel_UserName().from_dict(self.StartedBy)
		if(self.CancelledBy): self.CancelledBy = TgsModel_UserName().from_dict(self.CancelledBy)

class TgsModel_ByondInstallResponse(TgsModel_FileTicketResponse):
	InstallJob: TgsModel_JobResponse = None

	def sanitize(self):
		super().sanitize()
		if(self.InstallJob): self.InstallJob = TgsModel_JobResponse().from_dict(self.InstallJob)

class TgsModel_ByondResponse(TgsModelBase):
	Version: str = None

class TgsModel_ChatProvider(Enum):
	Irc = "Irc"
	Discord = "Discord"

class TgsModel_ChatBotSettings(TgsModel_NamedEntity):
	Enabled: bool = None
	ReconnectionInterval: int = None
	ChannelLimit: int = None
	Provider: TgsModel_ChatProvider = None
	ConnectionString: str = None

class TgsModel_ChatChannel(TgsModelBase):
	IrcChannel: str = None
	DiscordChannelId: int = None
	IsAdminChannel: bool = None
	IsWatchdogChannel: bool = None
	IsUpdatesChannel: bool = None
	Tag: str = None

class TgsModel_ChatBotApiBase(TgsModel_ChatBotSettings):
	Channels: 'list[TgsModel_ChatChannel]' = None

	def sanitize(self):
		super().sanitize()
		_l = list()
		for entry in self.Channels: _l.append(TgsModel_ChatChannel().from_dict(entry))
		self.Channels = _l

class TgsModel_ChatBotResponse(TgsModel_ChatBotApiBase):
	pass

class TgsModel_TestMergeParameters(TgsModelBase):
	Number: int = None
	TargetCommitSha: str = None
	Comment: str = None

class TgsModel_TestMergeModelBase(TgsModel_TestMergeParameters):
	TitleAtMerge: str = None
	BodyAtMerge: str = None
	Url: str = None
	Author: str = None

class TgsModel_TestMergeApiBase(TgsModel_TestMergeModelBase):
	Id: int = None
	MergedAt: datetime = None

	def sanitize(self):
		super().sanitize()
		self.MergedAt = tgs_datetime(self.MergedAt)

class TgsModel_TestMerge(TgsModel_TestMergeApiBase):
	MergedBy: TgsModel_UserName = None

	def sanitize(self):
		super().sanitize()
		self.MergedBy = TgsModel_UserName().from_dict(self.MergedBy)

class TgsModel_RevisionInformation_Internal(TgsModelBase):
	CommitSha: str = None
	Timestamp: datetime = None
	OriginCommitSha: str = None

	def sanitize(self):
		super().sanitize()
		self.Timestamp = tgs_datetime(self.Timestamp)

class TgsModel_RevisionInformation(TgsModel_RevisionInformation_Internal):
	PrimaryTestMerge: TgsModel_TestMerge = None
	ActiveTestMerges: 'list[TgsModel_TestMerge]' = None
	CompileJobs: 'list[TgsModel_EntityId]' = None

	def sanitize(self):
		super().sanitize()
		if(self.PrimaryTestMerge): self.PrimaryTestMerge = TgsModel_TestMerge().from_dict(self.PrimaryTestMerge)
		_l = list()
		for tm in self.ActiveTestMerges:
			_l.append(TgsModel_TestMerge().from_dict(tm))
		self.ActiveTestMerges = _l
		_l = list()
		for cj in self.CompileJobs:
			_l.append(TgsModel_EntityId().from_dict(cj))
		self.CompileJobs = _l

class TgsModel_DreamDaemonSecurity(Enum):
	Trusted = 0
	Safe = 1
	Ultrasafe = 1

class TgsModel_CompileJob(TgsModel_EntityId):
	DmeName: str = None
	Output: str = None
	DirectoryName: UUID = None
	MinimumSecurityLevel: TgsModel_DreamDaemonSecurity = None
	DMApiVersion: str = None

class TgsModel_CompileJobResponse(TgsModel_CompileJob):
	Job: TgsModel_JobResponse = None
	RevisionInformation: TgsModel_RevisionInformation = None
	ByondVersion: str = None
	RepositoryOrigin: str = None

	def sanitize(self):
		super().sanitize()
		if(self.Job): self.Job = TgsModel_JobResponse().from_dict(self.Job)
		if(self.RevisionInformation): self.RevisionInformation = TgsModel_RevisionInformation().from_dict(self.RevisionInformation)

class TgsModel_IConfigurationFile(TgsModelBase):
	Path: str = None
	LastReadHash: str = None

class TgsModel_ConfigurationFileResponse(TgsModel_FileTicketResponse, TgsModel_IConfigurationFile):
	Path: str = None
	LastReadHash: str = None
	IsDirectory: bool = None
	AccessDenied: bool = None

class TgsModel_DreamDaemonVisibility(Enum):
	Public = 0
	Private = 1
	Invisible = 2

class TgsModel_WatchdogStatus(Enum):
	Offline = 0
	Restoring = 1
	Online = 2
	DelayedRestart = 3

class TgsModel_DreamDaemonLaunchParameters(TgsModelBase):
	AllowWebClient: bool = None
	Visibility: TgsModel_DreamDaemonVisibility = None
	SecurityLevel: TgsModel_DreamDaemonSecurity = None
	Port: int = None
	StartupTimeout: int = None
	HeartbeatSeconds: int = None
	TopicRequestTimeout: int = None
	AdditionalParameters: str = None

class TgsModel_DreamDaemonSettings(TgsModel_DreamDaemonLaunchParameters):
	AutoStart: bool = None

class TgsModel_DreamDaemonApiBase(TgsModel_DreamDaemonSettings):
	SoftRestart: bool = None
	SoftShutdown: bool = None

class TgsModel_DreamDaemonResponse(TgsModel_DreamDaemonApiBase):
	ActiveCompileJob: TgsModel_CompileJobResponse = None
	StagedCompileJob: TgsModel_CompileJobResponse = None
	Status: TgsModel_WatchdogStatus = None
	CurrentSecurity: TgsModel_DreamDaemonSecurity = None
	CurrentVisibility: TgsModel_DreamDaemonVisibility = None
	CurrentPort: int = None
	CurrentAllowWebclient: bool = None

	def sanitize(self):
		super().sanitize()
		if(self.ActiveCompileJob): self.ActiveCompileJob = TgsModel_CompileJobResponse().from_dict(self.ActiveCompileJob)
		if(self.StagedCompileJob): self.StagedCompileJob = TgsModel_CompileJobResponse().from_dict(self.StagedCompileJob)

class TgsModel_DreamMakerSettings(TgsModelBase):
	ProjectName: str = None
	ApiValidationPort: int = None
	ApiValidationSecurityLevel: TgsModel_DreamDaemonSecurity = None
	RequireDMApiValidation: bool = None
	Timeout: timedelta = None

class TgsModel_ErrorMessageResponse(TgsModelBase, IOError):
	ServerApiVersion: str = None
	Message: str = None
	AdditionalData: str = None
	ErrorCode: TgsModel_ErrorCode = None

	def __str__(self) -> str:
		return "{}: {}".format(self.__class__.__name__, self.Message)

class TgsModel_DreamMakerResponse(TgsModel_DreamMakerSettings):
	pass

class TgsModel_InstancePermissionSetRights(Flag):
	Read = 1
	Write = 2
	Create = 4

class TgsModel_ByondRights(Flag):
	ReadActive = 1
	ListInstalled = 2
	InstallOfficialOrChangeActiveVersion = 4
	CancelInstall = 8
	InstallCustomVersion = 16

class TgsModel_DreamDaemonRights(Flag):
	ReadRevision = 1
	SetPort = 2
	SetAutoStart = 4
	SetSecurity = 8
	ReadMetadata = 16
	SetWebClient = 32
	SoftRestart = 64
	SoftShutdown = 128
	Restart = 256
	Shutdown = 512
	Start = 1024
	SetStartupTimeout = 2048
	SetHeartbeatInterval = 4096
	CreateDump = 8192
	SetTopicTimeout = 16384
	SetAdditionalParameters = 32768
	SetVisibility = 65536

class TgsModel_DreamMakerRights(Flag):
	Read = 1
	Compile = 2
	CancelCompile = 4
	SetDme = 8
	SetApiValidationPort = 16
	CompileJobs = 32
	SetSecurityLevel = 64
	SetApiValidationRequirement = 128
	SetTimeout = 256

class TgsModel_RepositoryRights(Flag):
	CancelPendingChanges = 1
	SetOrigin = 2
	SetSha = 4
	MergePullRequest = 8
	UpdateBranch = 16
	ChangeCommitter = 32
	ChangeTestMergeCommits = 64
	ChangeCredentials = 128
	SetReference = 256
	Read = 512
	ChangeAutoUpdateSettings = 1024
	Delete = 2048
	CancelClone = 4096
	ChangeSubmoduleUpdate = 8192

class TgsModel_ChatBotRights(Flag):
	WriteEnabled = 1
	WriteProvider = 2
	WriteChannels = 4
	WriteConnectionString = 8
	ReadConnectionString = 16
	Read = 32
	Create = 64
	Delete = 128
	WriteName = 256
	WriteReconnectionInterval = 512
	WriteChannelLimit = 1024

class TgsModel_ConfigurationRights(Flag):
	Read = 1
	Write = 2
	List = 4
	Delete = 8

class TgsModel_InstancePermissionSet(TgsModelBase):
	PermissionSetId: int = None
	InstancePermissionSetRights: TgsModel_InstancePermissionSetRights = None
	ByondRights: TgsModel_ByondRights = None
	DreamDaemonRights: TgsModel_DreamDaemonRights = None
	DreamMakerRights: TgsModel_DreamMakerRights = None
	RepositoryRights: TgsModel_RepositoryRights = None
	ChatBotRights: TgsModel_ChatBotRights = None
	ConfigurationRights: TgsModel_ConfigurationRights = None

class TgsModel_InstancePermissionSetResponse(TgsModel_InstancePermissionSet):
	pass

class TgsModel_ConfigurationType(Enum):
	Disallowed = 0
	HostWrite = 1
	SystemIdentityWrite = 2

class TgsModel_Instance(TgsModel_NamedEntity):
	Path: str = None
	Online: bool = None
	ConfigurationType: TgsModel_ConfigurationType = None
	AutoUpdateInterval: int = None
	ChatBotLimit: int = None

class TgsModel_InstanceResponse(TgsModel_Instance):
	MoveJob: TgsModel_JobResponse = None
	Accessible: bool = None

	def sanitize(self):
		super().sanitize()
		if(self.MoveJob): self.MoveJob = TgsModel_JobResponse().from_dict(self.MoveJob)

class TgsModel_LogFileResponse(TgsModel_FileTicketResponse):
	Name: str = None
	LastModified: datetime = None

	def sanitize(self):
		super().sanitize()
		self.LastModified = tgs_datetime(self.LastModified)

class TgsModel_PaginatedResponse(TgsModelBase, Iterable):
	TotalItems: int = None
	PageSize: int = None
	TotalPages: int = None
	Content: 'list[dict]' = None

	def __iter__(self) -> Iterator:
		for entry in self.Content:
			yield entry

	def iter_as(self, cls) -> list:
		_l = list()
		for entry in self.Content:
			_l.append(cls().from_dict(entry))
		return _l

class TgsModel_RemoteGitProvider(Enum):
	Unknown = "Unknown"
	GitHub = "GitHub"
	GitLab = "GitLab"

class TgsModel_RepositorySettings(TgsModelBase):
	CommitterName: str = None
	CommitterEmail: str = None
	AccessUser: str = None
	AccessToken: str = None
	PushTestMergeCommits: bool = None
	CreateGitHubDeployments: bool = None
	ShowTestMergeCommitters: bool = None
	AutoUpdatesKeepTestMerges: bool = None
	AutoUpdatesSynchronize: bool = None
	PostTestMergeComment: bool = None
	UpdateSubmodules: bool = None

class TgsModel_RepositoryApiBase(TgsModel_RepositorySettings):
	Reference: str = None

class TgsModel_IGitRemoteInformation(TgsModelBase):
	RemoteGitProvider: TgsModel_RemoteGitProvider = None
	RemoteRepositoryOwner: str = None
	RemoteRepositoryName: str = None

class TgsModel_RepositoryResponse(TgsModel_RepositoryApiBase, TgsModel_IGitRemoteInformation):
	Origin: str = None
	RevisionInformation: TgsModel_RevisionInformation = None
	RemoteGitProvider: TgsModel_RemoteGitProvider = None
	RemoteRepositoryOwner: str = None
	RemoteRepositoryName: str = None
	ActiveJob: TgsModel_JobResponse = None

	def sanitize(self):
		super().sanitize()
		if(self.RevisionInformation): self.RevisionInformation = TgsModel_RevisionInformation().from_dict(self.RevisionInformation)
		if(self.ActiveJob): self.ActiveJob = TgsModel_JobResponse().from_dict(self.ActiveJob)

class TgsModel_OAuthProviderInfo(TgsModelBase):
	ClientId: str = None
	RedirectUri: str = None
	ServerUrl: str = None

class TgsModel_SwarmServer(TgsModelBase):
	Address: str = None
	Identifier: str = None

class TgsModel_SwarmServerResponse(TgsModel_SwarmServer):
	Controller: bool = None

class TgsModel_ServerInformationBase(TgsModelBase):
	MinimumPasswordLength: int = None
	InstanceLimit: int = None
	UserLimit: int = None
	UserGroupLimit: int = None
	ValidInstancePaths: 'list[str]' = None

class TgsModel_ServerInformationResponse(TgsModel_ServerInformationBase):
	Version: str = None
	ApiVersion: str = None
	DMApiVersion: str = None
	WindowsHost: bool = None
	UpdateInProgress: bool = None
	SwarmServers: 'list[TgsModel_SwarmServerResponse]' = None
	OAuthProviderInfos: 'dict[TgsModel_OAuthProvider, TgsModel_OAuthProviderInfo]' = None

	def sanitize(self):
		super().sanitize()
		_l = list()
		for _dict in self.SwarmServers:
			_l.append(TgsModel_SwarmServerResponse().from_dict(_dict))
		self.SwarmServers = _l
		_d = dict()
		for k, v in self.OAuthProviderInfos:
			_d[k] = TgsModel_OAuthProviderInfo().from_dict(v)
		self.OAuthProviderInfos = _d

class TgsModel_ServerUpdate(TgsModelBase):
	NewVersion: str = None

class TgsModel_ServerUpdateResponse(TgsModel_ServerUpdate):
	pass

class TgsModel_ServerUpdateRequest(TgsModel_ServerUpdate):
	pass

class TgsModel_TokenResponse(TgsModelBase):
	Bearer: str = None
	ExpiresAt: datetime = None

	def sanitize(self):
		super().sanitize()
		self.ExpiresAt = tgs_datetime(self.ExpiresAt)

class TgsModel_UserGroupResponse(TgsModel_UserGroup):
	Users: 'list[TgsModel_UserName]' = None

	def sanitize(self):
		super().sanitize()
		_l = list()
		for dict in self.Users:
			_l.append(TgsModel_UserName().from_dict(dict))
		self.Users = _l

class TgsModel_ByondVersionRequest(TgsModelBase):
	Version: str = None
	UploadCustomZip: bool = None

class TgsModel_ChatBotCreateRequest(TgsModel_ChatBotApiBase):
	pass

class TgsModel_ChatBotUpdateRequest(TgsModel_ChatBotApiBase):
	pass

class TgsModel_ConfigurationFileRequest(TgsModel_IConfigurationFile):
	pass

class TgsModel_DreamDaemonRequest(TgsModel_DreamDaemonApiBase):
	pass

class TgsModel_DreamMakerRequest(TgsModel_DreamMakerSettings):
	pass

class TgsModel_InstanceCreateRequest(TgsModel_Instance):
	pass

class TgsModel_InstancePermissionSetRequest(TgsModel_InstancePermissionSet):
	pass

class TgsModel_InstanceUpdateRequest(TgsModel_Instance):
	pass

class TgsModel_RepositoryCreateRequest(TgsModel_RepositoryApiBase):
	Origin: str = None
	### obsolete
	_RecurseSubmodules: bool = None

class TgsModel_RepositoryUpdateRequest(TgsModel_RepositoryApiBase):
	CheckoutSha: str = None
	UpdateFromOrigin: bool = None
	NewTestMerges: 'list[TgsModel_TestMergeParameters]' = None

class TgsModel_UserUpdateRequest(TgsModel_UserApiBase):
	Password: str = None

class TgsModel_UserCreateRequest(TgsModel_UserUpdateRequest):
	pass

class TgsModel_UserGroupUpdateRequest(TgsModel_UserGroup):
	pass

class TgsModel_UserGroupCreateRequest(TgsModel_UserGroupUpdateRequest):
	pass

class TgsModel_DiscordDMOutputDisplayType(Enum):
	Always = 0
	OnError = 1
	Never = 2

# class TgsModel_FileResult(TgsModelBase):
# 	ContentType: str = None
# 	FileDownloadName: str = None
# 	LastModified: datetime = None
# 	EnableRangeProcessing: bool = None
# 	EntityTag: EntityTagHeaderValue = None

# class TgsModel_LimitedFileStreamResult(TgsModel_FileResult):
# 	FileStream: bytes = None
