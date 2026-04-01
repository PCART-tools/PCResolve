import requests
import numpy as np

FUNCS_LIST=[
    requests.get,
    np.sum,
    requests.post,
]

FUNCS_TUP=(
    np.mean,
    requests.put,
)

FUNCS_SET={requests.delete,np.max}