import multiprocessing as mp


def handle(item):
    name, count = item
    name.strip()
    count.bit_length()


def make_unknown_item():
    return object()


def handle_mixed(item):
    value, = item
    value.strip()


items = []
items.append(("name", 1))
pool = mp.Pool(1)
pool.map(handle, items)

mixed_items = []
mixed_items.append(("known",))
mixed_items.append(make_unknown_item())
pool.map(handle_mixed, mixed_items)
