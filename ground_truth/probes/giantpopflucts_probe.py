#!/usr/bin/env python3
## @package ground_truth.probes.giantpopflucts_probe
#  Minimal receiver-ownership probes for giantpopflucts GT records.

import inspect


## Return the defining module name for a callable when available.
#  @param value Callable or descriptor to inspect.
#  @return Module name or an empty string.
def _module_name(value):
    module = inspect.getmodule(value)
    return module.__name__ if module is not None else ""


## Verify that Seaborn plot results expose Matplotlib-owned receivers.
def probe_seaborn_matplotlib_receivers():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    print("seaborn version:", sns.__version__)
    print("matplotlib version:", matplotlib.__version__)

    axes_by_plotter = {
        "barplot": sns.barplot(x=["a", "b"], y=[1.0, 2.0]),
        "stripplot": sns.stripplot(x=["a", "b"], y=[1.0, 2.0]),
        "swarmplot": sns.swarmplot(x=["a", "b"], y=[1.0, 2.0]),
    }
    for name, axes in axes_by_plotter.items():
        print("%s axes type module:" % name, type(axes).__module__)
        print("%s legend method module:" % name, _module_name(
            axes.get_legend_handles_labels))
        assert type(axes).__module__.split(".")[0] == "matplotlib"
        assert _module_name(
            axes.get_legend_handles_labels).split(".")[0] == "matplotlib"

    axes = axes_by_plotter["barplot"]
    patch = axes.patches[0]
    print("patch type module:", type(patch).__module__)
    print("get_x method module:", _module_name(patch.get_x))
    print("get_width method module:", _module_name(patch.get_width))
    print("get_height method module:", _module_name(patch.get_height))

    assert type(patch).__module__.split(".")[0] == "matplotlib"
    assert _module_name(patch.get_x).split(".")[0] == "matplotlib"
    assert _module_name(patch.get_width).split(".")[0] == "matplotlib"
    assert _module_name(patch.get_height).split(".")[0] == "matplotlib"
    for axes in axes_by_plotter.values():
        plt.close(axes.figure)


## Verify the result owner of the project's np.log lambda transform.
def probe_numpy_log_result():
    import numpy as np

    transform = lambda value: np.log(value)
    result = transform(np.array([[1.0, 2.0]]))

    print("numpy version:", np.__version__)
    print("log result type module:", type(result).__module__)
    print("flatten bound receiver:", result.flatten.__self__ is result)

    assert type(result).__module__.split(".")[0] == "numpy"
    assert result.flatten.__self__ is result


## Verify ownership of scipy.stats.norm().ppf.
def probe_scipy_frozen_distribution():
    import scipy
    import scipy.stats

    distribution = scipy.stats.norm()
    method = distribution.ppf

    print("scipy version:", scipy.__version__)
    print("distribution type module:", type(distribution).__module__)
    print("ppf method module:", _module_name(method))
    print("ppf bound receiver:", method.__self__ is distribution)

    assert type(distribution).__module__.split(".")[0] == "scipy"
    assert _module_name(method).split(".")[0] == "scipy"
    assert method.__self__ is distribution


## Run all giantpopflucts ownership probes.
def main():
    probe_seaborn_matplotlib_receivers()
    probe_numpy_log_result()
    probe_scipy_frozen_distribution()
    print("all probes passed")


if __name__ == "__main__":
    main()
