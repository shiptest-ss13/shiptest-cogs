from py_tgs.tgs_api_models import *
from py_tgs.tgs_api_defs import *

address = "https://tgs.shiptest.net/"
resp = tgs_login(address, "dragon", "3VSeMT2L331kJ^!9Ay")
print(resp.Bearer)

# ?tgslink login dragon BP2FfIKQrr7h