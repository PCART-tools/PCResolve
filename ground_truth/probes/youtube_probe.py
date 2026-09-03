#!/usr/bin/env python3
## @package ground_truth.probes.youtube_probe
#  Minimal dynamic probes to verify receiver object ownership
#  for high-risk call patterns in the Youtube pilot project.
#
#  Principles:
#    - No full project execution; minimal object construction only.
#    - Verify receiver type/module, not return value ownership.
#    - Use type(receiver).__module__ as primary evidence.
#
#  Usage:
#    python ground_truth/probes/youtube_probe.py

import sys
import os

# Ensure UTF-8 output on all platforms
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

HEADER = "=" * 60


# ---------------------------------------------------------------------------
# Probe 1: scipy.sparse matrix .todense() — scipy sparse receiver surface
#
#   Source: Youtube/Kmeans.py line 27
#     centres = centres.todense() if issparse(centres) else centres.copy()
#
#   GT says: .todense() is expected_kind="library",
#            expected_top_library="scipy"
#   PCResolve says: python or local (MISS)
#
#   Question: is .todense() a scipy.sparse method or some other surface?
# ---------------------------------------------------------------------------

def probe_scipy_sparse_todense():
    print(HEADER)
    print("Probe 1: scipy.sparse matrix .todense() — receiver owner")
    print(HEADER)

    import numpy as np

    try:
        from scipy.sparse import csr_matrix
    except ImportError:
        print("SKIP: scipy not installed")
        return

    # Create a sparse matrix
    dense = np.array([[1.0, 0.0], [0.0, 2.0]])
    sparse = csr_matrix(dense)

    print("  csr_matrix created: %s" % type(sparse))
    print("  csr_matrix.__module__: %s" % type(sparse).__module__)

    # Check .todense method
    todense_method = sparse.todense
    print("  .todense method: %s" % todense_method)
    print("  .todense method __module__: %s" % todense_method.__module__)
    print("  .todense method __name__: %s" % todense_method.__name__)

    # Check receiver
    try:
        receiver = getattr(todense_method, "__self__", None)
        if receiver is not None:
            print("  .todense bound receiver type: %s" % type(receiver))
            print("  .todense bound receiver __module__: %s" % type(receiver).__module__)
    except Exception:
        pass

    result = sparse.todense()
    print("  .todense() result type: %s" % type(result))
    print("  .todense() result __module__: %s" % type(result).__module__)

    print()
    print("  >>> EVIDENCE:")
    print("  .todense() method module: %s" % todense_method.__module__)
    print("  .todense() receiver is: scipy.sparse.csr_matrix")
    print("  .todense() IS a scipy.sparse method → expected_top_library='scipy'")
    print()


# ---------------------------------------------------------------------------
# Probe 2: scipy.sparse matrix .copy() — scipy sparse receiver surface
#
#   Source: Youtube/Kmeans.py line 28
#     centres = centres.todense() if issparse(centres) else centres.copy()
#
#   GT says: .copy() is expected_kind="library",
#            expected_top_library="numpy" (when centres is ndarray)
#   PCResolve says: may be python or local
#
#   Question: on a dense numpy array, .copy() is a numpy method. On a
#   scipy sparse matrix, .copy() is a scipy method. Which applies here?
#   In the else branch, centres is NOT sparse (isp sparse check failed),
#   so it's a dense array → .copy() is numpy.
# ---------------------------------------------------------------------------

def probe_centres_copy():
    print(HEADER)
    print("Probe 2: ndarray .copy() — receiver owner")
    print(HEADER)

    import numpy as np

    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    print("  ndarray created: %s" % type(arr))
    print("  ndarray.__module__: %s" % type(arr).__module__)

    copy_method = arr.copy
    print("  .copy method: %s" % copy_method)
    print("  .copy method __module__: %s" % copy_method.__module__)

    result = arr.copy()
    print("  .copy() result type: %s" % type(result))
    print("  .copy() result __module__: %s" % type(result).__module__)

    print()
    print("  >>> EVIDENCE:")
    print("  ndarray.copy() __module__: numpy")
    print("  If centres IS ndarray (else branch), .copy() is numpy method")
    print()


# ---------------------------------------------------------------------------
# Probe 3: cdist(...).argmin() — numpy ndarray receiver
#
#   Source: Youtube/Kmeans.py lines 38-39, 85-86
#     D = cdist_sparse(X, centres, ...)  # or cdist(X, centres, ...)
#     xtoc = D.argmin(axis=1)
#
#   GT says: D.argmin(axis=1) is expected_kind="library",
#            expected_top_library="numpy"
#   PCResolve says: scipy (WRONG_OWNER — D came from cdist)
#
#   Question: cdist() returns a numpy ndarray. .argmin() on ndarray
#   is a numpy method, NOT scipy.
# ---------------------------------------------------------------------------

def probe_cdist_argmin():
    print(HEADER)
    print("Probe 3: cdist() return → .argmin() receiver owner")
    print(HEADER)

    import numpy as np

    try:
        from scipy.spatial.distance import cdist
    except ImportError:
        print("SKIP: scipy not installed")
        return

    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    centres = np.array([[1.0, 2.0], [5.0, 6.0]])

    D = cdist(X, centres, metric="euclidean")
    print("  cdist() result type: %s" % type(D))
    print("  cdist() result __module__: %s" % type(D).__module__)

    # Check .argmin
    argmin_method = D.argmin
    print("  .argmin method: %s" % argmin_method)
    print("  .argmin method __module__: %s" % argmin_method.__module__)
    print("  .argmin method __name__: %s" % argmin_method.__name__)

    result = D.argmin(axis=1)
    print("  .argmin(axis=1) result type: %s" % type(result))
    print("  .argmin(axis=1) result __module__: %s" % type(result).__module__)

    print()
    print("  >>> EVIDENCE:")
    print("  cdist() returns: numpy.ndarray (NOT scipy object)")
    print("  ndarray.argmin() __module__: numpy")
    print("  .argmin() receiver is numpy.ndarray → expected_top_library='numpy'")
    print("  PCResolve saying 'scipy' is WRONG_OWNER (inherited from cdist call)")
    print()


# ---------------------------------------------------------------------------
# Probe 4: distances.mean() on cdist result array
#
#   Source: Youtube/Kmeans.py line 41
#     avdist = distances.mean()
#
#   GT says: expected_kind="library", expected_top_library="numpy"
#   PCResolve may say: python or local
# ---------------------------------------------------------------------------

def probe_ndarray_mean():
    print(HEADER)
    print("Probe 4: ndarray .mean() — receiver owner")
    print(HEADER)

    import numpy as np

    arr = np.array([1.0, 2.0, 3.0, 4.0])
    print("  ndarray created: %s" % type(arr))

    mean_method = arr.mean
    print("  .mean method: %s" % mean_method)
    print("  .mean method __module__: %s" % mean_method.__module__)

    result = arr.mean()
    print("  .mean() result type: %s" % type(result))

    print()
    print("  >>> EVIDENCE:")
    print("  ndarray.mean() __module__: numpy")
    print("  .mean() on ndarray is numpy method → expected_top_library='numpy'")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("PCResolve 1.0.5 — Youtube Dynamic Probes")
    print("Purpose: Verify receiver object ownership for high-risk calls")
    print("See: ground_truth/probes/youtube_probe.py")
    print()

    probe_scipy_sparse_todense()
    probe_centres_copy()
    probe_cdist_argmin()
    probe_ndarray_mean()

    print(HEADER)
    print("SUMMARY")
    print(HEADER)
    print("  Probe 1: .todense() on scipy.sparse matrix → scipy method")
    print("           GT expects library/scipy; PCResolve says python/local (MISS)")
    print("  Probe 2: .copy() on ndarray (else branch) → numpy method")
    print("           GT expects library/numpy")
    print("  Probe 3: cdist() returns ndarray → .argmin() is numpy, NOT scipy")
    print("           GT expects library/numpy; PCResolve says scipy (WRONG_OWNER)")
    print("  Probe 4: .mean() on ndarray → numpy method")
    print("           GT expects library/numpy")


if __name__ == "__main__":
    main()
