# Negative cases: local/parameter receivers must NOT become unknown.
# These reproduce real regression patterns from tested_projects.
# No module-level calls needed — function bodies are visited during AST
# analysis and calls inside are collected regardless.

import numpy as np


def tokenize(s):
    s = s.strip()               # parameter receiver: must stay local


def label(experiment, pivot):
    experiment = experiment.replace(pivot + "-lint-", "")
    experiment = experiment.replace("-", " ").title()
    return experiment           # parameter receiver with chained calls


def process(X, Xd, expTime, correction):
    Xr = np.divide(X, (Xd + 1e-8))
    Xr = Xr / (expTime * correction)
    Xr = Xr * 4
    Xr.astype("float32")        # local var after arithmetic: must stay local


# Real SDOML pattern
def aia_fits_to_np(data):
    Xr = data
    Xr.astype(np.float64)       # local assignment: must stay local
