## @package pcresolve.fact_versions
#  Mutation notifications for internal facts; versions are not schema fields.


## Ordered dictionary with constant-cost mutation generation.
class VersionedDict(dict):
    ## Copy entries and callbacks using one memo to preserve observer identities.
    #  @param memo Existing deepcopy identity map.
    #  @return Detached ordered dictionary.
    def __deepcopy__(self, memo):
        from copy import deepcopy
        copied = type(self)()
        memo[id(self)] = copied
        for key, value in self.items():
            dict.__setitem__(copied, deepcopy(key, memo), deepcopy(value, memo))
        copied.__dict__.update(deepcopy(self.__dict__, memo))
        return copied

    ## Initialize entries and optional change/insertion callbacks.
    def __init__(self, values=(), changed=None, adopt=None):
        super().__init__(values)
        self.version = 0
        self._changed, self._adopt = changed, adopt
        if adopt is not None:
            for value in self.values():
                adopt(value)

    def _touch(self):
        self.version += 1
        if self._changed is not None:
            self._changed()

    def __setitem__(self, key, value):
        if self._adopt is not None:
            self._adopt(value)
        super().__setitem__(key, value)
        self._touch()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._touch()

    ## Insert dictionary-compatible entries and notify each successful write.
    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    ## Return an existing entry or insert and notify its default.
    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    ## Remove one present entry and notify; missing defaults do not change facts.
    def pop(self, key, *default):
        present = key in self
        value = super().pop(key, *default)
        if present:
            self._touch()
        return value

    ## Remove the last ordered entry and notify the change.
    def popitem(self):
        value = super().popitem()
        self._touch()
        return value

    ## Remove all present entries and notify once.
    def clear(self):
        if self:
            super().clear()
            self._touch()

    def __ior__(self, other):
        self.update(other)
        return self


## List notifying changes while retaining ordinary sequence operations.
class VersionedList(list):
    ## Copy elements and callbacks using one memo to preserve observer identities.
    #  @param memo Existing deepcopy identity map.
    #  @return Detached ordered list.
    def __deepcopy__(self, memo):
        from copy import deepcopy
        copied = type(self)()
        memo[id(self)] = copied
        for value in self:
            list.append(copied, deepcopy(value, memo))
        copied.__dict__.update(deepcopy(self.__dict__, memo))
        return copied

    ## Initialize elements and optional change/insertion callbacks.
    def __init__(self, values=(), changed=None, adopt=None):
        super().__init__(values)
        self.version = 0
        self._changed, self._adopt = changed, adopt
        if adopt is not None:
            for value in self:
                adopt(value)

    def _touch(self):
        self.version += 1
        if self._changed is not None:
            self._changed()

    def _observe(self, value):
        if self._adopt is not None:
            self._adopt(value)

    ## Observe and append one element, then notify its insertion.
    def append(self, value):
        self._observe(value)
        super().append(value)
        self._touch()

    ## Append elements in order, retaining partial updates if an iterator fails.
    def extend(self, values):
        # Snapshot self-extension; other iterators keep partial-update semantics.
        for value in (list(values) if values is self else values):
            self.append(value)

    ## Observe and insert one element at a list-compatible position.
    def insert(self, index, value):
        self._observe(value)
        super().insert(index, value)
        self._touch()

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            value = list(value)
            for item in value:
                self._observe(item)
        else:
            self._observe(value)
        super().__setitem__(index, value)
        self._touch()

    def __delitem__(self, index):
        super().__delitem__(index)
        self._touch()

    ## Remove one element and notify its removal.
    def pop(self, index=-1):
        value = super().pop(index)
        self._touch()
        return value

    ## Remove the first matching element and notify its removal.
    def remove(self, value):
        super().remove(value)
        self._touch()

    ## Remove all present elements and notify once.
    def clear(self):
        if self:
            super().clear()
            self._touch()

    ## Reverse element order and notify dependent indexes.
    def reverse(self):
        super().reverse()
        self._touch()

    ## Sort elements and invalidate even when comparison leaves a partial change.
    def sort(self, *args, **kwargs):
        try:
            super().sort(*args, **kwargs)
        finally:
            self._touch()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        super().__imul__(count)
        self._touch()
        return self


## Records propagating collection changes to subscribed indexes.
class FactStructure:
    _versioned_fields = {}

    def _notify(self):
        self._version = getattr(self, '_version', 0) + 1
        for callback in tuple(getattr(self, '_listeners', ())):
            callback()

    ## Subscribe once to changes in indexed collections.
    #  @param callback Consumer invalidation callback.
    def watch(self, callback):
        if not hasattr(self, '_listeners'):
            self._listeners = []
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _adopt(self, value):
        if isinstance(value, FactStructure):
            value.watch(self._notify)

    def __setattr__(self, name, value):
        collection = self._versioned_fields.get(name)
        if collection is not None:
            value = collection(value, changed=self._notify, adopt=self._adopt)
        object.__setattr__(self, name, value)
        if collection is not None:
            self._notify()

    ## Current structural generation; reading it does not scan children.
    @property
    def version(self):
        return getattr(self, '_version', 0)
