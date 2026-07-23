from package_a import Widget


def use_selected():
    selected = widgets[input()]
    return selected.run()


def use_mixed():
    selected = mixed[input()]
    return selected.run()


widgets = {
    "left": Widget(),
    "right": Widget(),
}
mixed = {
    "left": Widget(),
    "right": Other(),
}
