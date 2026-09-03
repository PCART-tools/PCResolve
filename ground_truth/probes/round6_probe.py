#!/usr/bin/env python3
## @package ground_truth.probes.round6_probe
#  Reproducible receiver-ownership probes for Round 6 GT projects.

"""Verify the runtime ownership claims used by Round 6 ground truth."""

import importlib
import inspect
import tempfile
from pathlib import Path


def _top_module(value):
    return type(value).__module__.split(".", 1)[0]


def _method_module(method):
    module = inspect.getmodule(method)
    if module is None:
        return ""
    return module.__name__.split(".", 1)[0]


def _assert_method_owner(label, receiver, method_name, expected):
    method = getattr(receiver, method_name)
    receiver_owner = _top_module(receiver)
    implementation_owner = _method_module(method)
    print(
        "%s: receiver=%s implementation=%s bound=%s"
        % (
            label,
            receiver_owner,
            implementation_owner or "<builtin>",
            getattr(method, "__self__", None) is receiver,
        )
    )
    assert expected in (receiver_owner, implementation_owner)
    return method


def _assert_object_owner(label, value, expected):
    owner = _top_module(value)
    print("%s: owner=%s type=%s" % (label, owner, type(value).__name__))
    assert owner == expected


def _optional_module(name):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        print("SKIP %s: %s" % (name, exc))
        return None


def probe_python_receivers():
    values = []
    _assert_method_owner("list.append", values, "append", "builtins")

    text = "sample"
    _assert_method_owner("str.replace", text, "replace", "builtins")
    _assert_method_owner("str.join", text, "join", "builtins")
    _assert_method_owner("str.endswith", text, "endswith", "builtins")


def probe_numpy_receivers():
    np = _optional_module("numpy")
    if np is None:
        return

    array = np.arange(4.0)
    _assert_method_owner("ndarray.dot", array, "dot", "numpy")
    _assert_method_owner("ndarray.astype", array, "astype", "numpy")
    _assert_method_owner("ndarray.nonzero", array, "nonzero", "numpy")

    polynomial = np.poly1d([1.0, 2.0])
    _assert_object_owner("poly1d callable", polynomial, "numpy")
    _assert_object_owner("poly1d result", polynomial(array), "numpy")

    skimage_transform = _optional_module("skimage.transform")
    if skimage_transform is not None:
        reduced = skimage_transform.downscale_local_mean(
            np.arange(16.0).reshape(4, 4), (2, 2)
        )
        _assert_object_owner("downscale_local_mean result", reduced, "numpy")
        _assert_method_owner(
            "downscale_local_mean result astype", reduced, "astype", "numpy"
        )


def probe_pandas_receivers():
    pd = _optional_module("pandas")
    if pd is None:
        return

    frame = pd.DataFrame(
        {
            "year": [2020, 2021, 2021],
            "month": [1, 1, 2],
            "value": [1.0, 2.0, 3.0],
        }
    )
    indexed = _assert_method_owner(
        "DataFrame.set_index", frame, "set_index", "pandas"
    )("year")
    _assert_method_owner(
        "DataFrame.sort_index", indexed, "sort_index", "pandas"
    )
    _assert_method_owner("DataFrame.head", indexed, "head", "pandas")
    _assert_method_owner("DataFrame.hist", indexed, "hist", "pandas")
    _assert_method_owner("DataFrame.drop", indexed, "drop", "pandas")
    _assert_method_owner("DataFrame.reset_index", indexed, "reset_index", "pandas")

    series = frame["value"]
    _assert_method_owner("Series.mean", series, "mean", "pandas")
    _assert_method_owner("Series.median", series, "median", "pandas")
    _assert_method_owner("Series.hist", series, "hist", "pandas")
    grouped = _assert_method_owner(
        "Series.groupby", series, "groupby", "pandas"
    )(frame["month"])
    summed = _assert_method_owner("SeriesGroupBy.sum", grouped, "sum", "pandas")()
    _assert_object_owner("Series.plot accessor", summed.plot, "pandas")
    _assert_method_owner("PlotAccessor.bar", summed.plot, "bar", "pandas")


def probe_tsplib95_receiver():
    tsplib95 = _optional_module("tsplib95")
    if tsplib95 is None:
        return

    source = """NAME: tiny
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EUC_2D
NODE_COORD_SECTION
1 0 0
2 1 0
3 0 1
EOF
"""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "tiny.tsp"
        path.write_text(source, encoding="ascii")
        problem = tsplib95.load(str(path))
    _assert_method_owner(
        "tsplib95 problem.get_graph", problem, "get_graph", "tsplib95"
    )


def probe_porepy_receivers():
    pp = _optional_module("porepy")
    if pp is None:
        return

    np = _optional_module("numpy")
    if np is None:
        return

    grid = pp.CartGrid([2, 2], physdims=[100.0, 10.0])
    grid.compute_geometry()
    bucket = pp.GridBucket()
    bucket.add_nodes([grid])

    _assert_method_owner(
        "GridBucket.grids_of_dimension",
        bucket,
        "grids_of_dimension",
        "porepy",
    )
    _assert_method_owner("CartGrid.bounding_box", grid, "bounding_box", "porepy")
    _assert_method_owner(
        "CartGrid.cell_diameters", grid, "cell_diameters", "porepy"
    )
    _assert_method_owner("CartGrid.closest_cell", grid, "closest_cell", "porepy")
    boundary_faces = grid.tags["domain_boundary_faces"]
    _assert_method_owner(
        "domain_boundary_faces.nonzero", boundary_faces, "nonzero", "numpy"
    )


def main():
    probe_python_receivers()
    probe_numpy_receivers()
    probe_pandas_receivers()
    probe_tsplib95_receiver()
    probe_porepy_receivers()
    print("Round 6 ownership probes passed")


if __name__ == "__main__":
    main()
