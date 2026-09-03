def build_function_local_axes():
    import matplotlib.pyplot as mpl

    local_only_axes = mpl.gcf().add_subplot(111)
    local_only_axes.scatter([1], [2])
