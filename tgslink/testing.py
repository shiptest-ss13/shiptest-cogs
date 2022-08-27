from py_tgs.tgs_api_models import *
from py_tgs.tgs_api_defs import *

address = "https://tgs.shiptest.net/"
resp = tgs_login(address, "dragon", "BP2FfIKQrr7h#NVHqk")
print(resp.Bearer)
