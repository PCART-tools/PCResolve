import numpy as np
import seaborn as sns


transform = lambda value: np.log(value)
transformed = transform(np.array([1.0]))
transformed.flatten()


def build_containers():
    items = []
    items.append(1)

    grouped = {1: [], 2: []}
    key = 1
    grouped[key].append(2)


class Bag:
    def append(self, value):
        return value


def use_local_object():
    items = Bag()
    items.append(1)


axes = sns.barplot(data=[])
axes.get_legend_handles_labels()
for patch in axes.patches:
    patch.get_x()

strip_axes = sns.stripplot(data=[])
strip_axes.get_legend_handles_labels()
swarm_axes = sns.swarmplot(data=[])
swarm_axes.get_legend_handles_labels()


def build_annotated_container():
    typed_items: list = []
    typed_items.append(3)


class AttributeStore:
    def __init__(self):
        self.items = []
        self.grouped = {1: [], 2: []}

    def add(self, key):
        self.items.append(1)
        self.grouped[key].append(2)


class AttributeLocalObject:
    def __init__(self):
        self.items = Bag()

    def add(self):
        self.items.append(1)


class AnnotatedAttributeStore:
    def __init__(self):
        self.typed: list = []

    def add(self):
        self.typed.append(4)
