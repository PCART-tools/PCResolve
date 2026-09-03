import numpy as np
import pandas as pd

from provider import (
    Holder,
    conflicting_use,
    identity,
    recursive_identity,
    relay,
    use_value,
)


frame = pd.read_csv("data.csv")
array = np.array([1, 2, 3])

frame_result = identity(frame)
array_result = identity(array)
frame_result.head()
array_result.reshape(1, -1)

reused_result = identity(array)
reused_result.reshape(1, -1)
reused_result = identity(frame)
reused_result.head()

relay_result = relay(array)
relay_result.reshape(1, -1)

use_value(array)

conflicting_use(frame)
conflicting_use(array)

holder = Holder(frame)
held = holder.expose()
held.head()

recursive_result = recursive_identity(array, 1)
recursive_result.reshape(1, -1)
