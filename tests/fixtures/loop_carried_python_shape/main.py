class LocalValue:
    def add(self, value):
        return value


def collect(values):
    ready = False
    for value in values:
        if ready:
            carried.add(value)
        if value:
            carried = set()
            ready = True


def conflicting(values):
    carried = LocalValue()
    ready = False
    for value in values:
        if ready:
            carried.add(value)
        if value:
            carried = set()
            ready = True


def collect_while(values):
    index = 0
    ready = False
    while index < len(values):
        if ready:
            carried.append(values[index])
        carried = []
        ready = True
        index += 1


async def collect_async(values):
    ready = False
    async for value in values:
        if ready:
            carried.add(value)
        carried = set()
        ready = True


def tuple_conflicting(values, replacement):
    ready = False
    for value in values:
        if ready:
            carried.add(value)
        carried = set()
        if value:
            carried, other = replacement
        ready = True


def definition_conflicting(values):
    ready = False
    for value in values:
        if ready:
            carried.add(value)
        carried = set()

        def carried():
            return value

        ready = True
