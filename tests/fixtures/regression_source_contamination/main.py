# Regression fixture: source contamination (1.0.5 P0).
#
# Container methods on local builtin receivers must not inherit
# argument/element provenance as ApiCall.top_library.

import numpy as np
import pandas as pd

# ── list ──────────────────────────────────────────────────────────

lst = []
arr = np.array([1, 2, 3])
lst.append(arr[0])           # lst.append NOT numpy; receiver is local list
lst.append(np.float64(4.0))  # lst.append NOT numpy

lst2 = [1, 2]
lst2.extend([np.array([3])]) # lst2.extend NOT numpy

# ── dict ──────────────────────────────────────────────────────────

d = {}
series = pd.Series([1, 2], index=["a", "b"])
d.update(series)             # d.update NOT pandas; receiver is local dict

d["key"] = np.array([5])
d.get("key")                 # d.get NOT numpy

# ── set ───────────────────────────────────────────────────────────

s = set()
s.add(np.float64(1.0))       # s.add NOT numpy

# ── tuple ─────────────────────────────────────────────────────────

t = (1, 2, 3)
t.count(1)                   # t.count NOT numpy; stays local/python

# ── iteration contamination ───────────────────────────────────────

words = []
model_words = ["hello", "world"]
for word in model_words:
    words.append(word)        # words.append NOT from model_words iteration

# ── negative: third-party receiver must still work ─────────────────

arr2 = np.array([1, 2, 3])
arr2.reshape((1, 3))         # reshape IS numpy (third-party receiver)

df = pd.DataFrame({"a": [1]})
df.update(pd.DataFrame({"a": [2]}))  # df.update IS pandas (third-party receiver)
