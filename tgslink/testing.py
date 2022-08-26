from py_tgs.tgs_api_models import *
from py_tgs.tgs_api_defs import *

address = "http://127.0.0.1:5000"

user_token = tgs_login(address, "Admin", "ISolemlySwearToDeleteTheDataDirectory")
token = user_token.Bearer

try:
	req = TgsModel_ByondVersionRequest()
	req.Version = "514.1584"
	resp = tgs_byond_set_active(address, token, 1, req)
	print(resp)
except TgsModel_ErrorMessageResponse as err:
	print(err.Message)
