## @package pcresolve.ownership.fact_versions
#  Mutation notifications for internal facts; versions are not schema fields.
#  内部事实的变更通知；版本号不属于公共 schema 字段。

from typing import Callable, Optional


## Ordered dictionary with constant-cost mutation generation.
## 以常数开销记录变更代次的有序字典。
class VersionedDict(dict):
    _changed: Optional[Callable[[], None]]
    _adopt: Optional[Callable[[object], None]]

    ## Copy entries and callbacks using one memo to preserve observer identities.
    ## 使用同一 memo 复制条目与回调，保留观察者身份关系。
    #
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
    ## 初始化条目以及可选的变更、插入回调。
    #
    #  @param values Initial dictionary entries.
    #  @param changed Optional mutation callback.
    #  @param adopt Optional callback for inserted values.
    #  @return None
    def __init__(self, values=(), changed=None, adopt=None):
        super().__init__(values)
        self.version = 0
        self._changed, self._adopt = changed, adopt
        if adopt is not None:
            for value in self.values():
                adopt(value)

    ## Increment the generation and notify the observer.
    ## 递增代次并通知观察者。
    #
    #  @return None
    def _touch(self):
        self.version += 1
        if self._changed is not None:
            self._changed()

    ## Adopt and store an entry, then notify the mutation.
    ## 接管并存储条目，随后通知变更。
    #
    #  @param key Dictionary key.
    #  @param value Value to store.
    #  @return None
    def __setitem__(self, key, value):
        if self._adopt is not None:
            self._adopt(value)
        super().__setitem__(key, value)
        self._touch()

    ## Remove an entry and notify the mutation.
    ## 删除条目并通知变更。
    #
    #  @param key Dictionary key to remove.
    #  @return None
    def __delitem__(self, key):
        super().__delitem__(key)
        self._touch()

    ## Insert dictionary-compatible entries and notify each successful write.
    ## 写入字典兼容条目，并逐次通知成功写入。
    #
    #  @param args Positional inputs accepted by dict.
    #  @param kwargs Keyword entries to insert.
    #  @return None
    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    ## Return an existing entry or insert and notify its default.
    ## 返回已有条目，或插入默认值并通知。
    #
    #  @param key Dictionary key.
    #  @param default Value inserted when the key is absent.
    #  @return Existing or inserted value.
    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    ## Remove one present entry and notify; missing defaults do not change facts.
    ## 删除已有条目并通知；缺失时使用默认值不改变事实。
    #
    #  @param key Dictionary key.
    #  @param default Optional default accepted by dict.pop.
    #  @return Removed value or supplied default.
    def pop(self, key, *default):
        present = key in self
        value = super().pop(key, *default)
        if present:
            self._touch()
        return value

    ## Remove the last ordered entry and notify the change.
    ## 删除最后一个有序条目并通知变更。
    #
    #  @return Removed key and value pair.
    def popitem(self):
        value = super().popitem()
        self._touch()
        return value

    ## Remove all present entries and notify once.
    ## 清空已有条目并通知一次。
    #
    #  @return None
    def clear(self):
        if self:
            super().clear()
            self._touch()

    ## Merge entries using the notifying update operation.
    ## 使用带通知的更新操作合并条目。
    #
    #  @param other Entries to merge.
    #  @return This dictionary.
    def __ior__(self, other):
        self.update(other)
        return self


## List notifying changes while retaining ordinary sequence operations.
## 保留普通序列操作并通知变更的列表。
class VersionedList(list):
    _changed: Optional[Callable[[], None]]
    _adopt: Optional[Callable[[object], None]]

    ## Copy elements and callbacks using one memo to preserve observer identities.
    ## 使用同一 memo 复制元素与回调，保留观察者身份关系。
    #
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
    ## 初始化元素以及可选的变更、插入回调。
    #
    #  @param values Initial iterable of elements.
    #  @param changed Optional mutation callback.
    #  @param adopt Optional callback for inserted values.
    #  @return None
    def __init__(self, values=(), changed=None, adopt=None):
        super().__init__(values)
        self.version = 0
        self._changed, self._adopt = changed, adopt
        if adopt is not None:
            for value in self:
                adopt(value)

    ## Increment the generation and notify the observer.
    ## 递增代次并通知观察者。
    #
    #  @return None
    def _touch(self):
        self.version += 1
        if self._changed is not None:
            self._changed()

    ## Register an inserted value with the optional adoption callback.
    ## 通过可选接管回调注册插入的值。
    #
    #  @param value Value being inserted.
    #  @return None
    def _observe(self, value):
        if self._adopt is not None:
            self._adopt(value)

    ## Observe and append one element, then notify its insertion.
    ## 注册并追加一个元素，随后通知插入。
    #
    #  @param value Element to append.
    #  @return None
    def append(self, value):
        self._observe(value)
        super().append(value)
        self._touch()

    ## Append elements in order, retaining partial updates if an iterator fails.
    ## 按顺序追加元素；迭代器失败时保留已完成的部分更新。
    #
    #  @param values Iterable of elements to append.
    #  @return None
    def extend(self, values):
        # Snapshot self-extension; other iterators keep partial-update semantics.
        # 自身扩展先取快照，其他迭代器保留部分更新语义。
        for value in (list(values) if values is self else values):
            self.append(value)

    ## Observe and insert one element at a list-compatible position.
    ## 注册元素并在列表兼容的位置插入。
    #
    #  @param index Insertion index.
    #  @param value Element to insert.
    #  @return None
    def insert(self, index, value):
        self._observe(value)
        super().insert(index, value)
        self._touch()

    ## Replace one element or slice and notify the mutation.
    ## 替换单个元素或切片并通知变更。
    #
    #  @param index Element index or slice.
    #  @param value Replacement value or iterable for a slice.
    #  @return None
    def __setitem__(self, index, value):
        if isinstance(index, slice):
            value = list(value)
            for item in value:
                self._observe(item)
        else:
            self._observe(value)
        super().__setitem__(index, value)
        self._touch()

    ## Delete one element or slice and notify the mutation.
    ## 删除单个元素或切片并通知变更。
    #
    #  @param index Element index or slice.
    #  @return None
    def __delitem__(self, index):
        super().__delitem__(index)
        self._touch()

    ## Remove one element and notify its removal.
    ## 删除一个元素并通知。
    #
    #  @param index Index to remove; defaults to the last element.
    #  @return Removed element.
    def pop(self, index=-1):
        value = super().pop(index)
        self._touch()
        return value

    ## Remove the first matching element and notify its removal.
    ## 删除第一个匹配元素并通知。
    #
    #  @param value Element to remove.
    #  @return None
    def remove(self, value):
        super().remove(value)
        self._touch()

    ## Remove all present elements and notify once.
    ## 清空已有元素并通知一次。
    #
    #  @return None
    def clear(self):
        if self:
            super().clear()
            self._touch()

    ## Reverse element order and notify dependent indexes.
    ## 反转元素顺序并通知依赖索引。
    #
    #  @return None
    def reverse(self):
        super().reverse()
        self._touch()

    ## Sort elements and invalidate even when comparison leaves a partial change.
    ## 排序元素；即使比较中断导致部分变更也通知失效。
    #
    #  @param args Positional arguments forwarded to list.sort.
    #  @param kwargs Keyword arguments forwarded to list.sort.
    #  @return None
    def sort(self, *args, **kwargs):
        try:
            super().sort(*args, **kwargs)
        finally:
            self._touch()

    ## Extend in place with mutation notifications.
    ## 原位扩展并发送变更通知。
    #
    #  @param values Iterable of elements.
    #  @return This list.
    def __iadd__(self, values):
        self.extend(values)
        return self

    ## Repeat in place and notify dependent indexes.
    ## 原位重复元素并通知依赖索引。
    #
    #  @param count Repetition count.
    #  @return This list.
    def __imul__(self, count):
        super().__imul__(count)
        self._touch()
        return self


## Records propagating collection changes to subscribed indexes.
## 将集合变更传播给已订阅索引的记录。
class FactStructure:
    _versioned_fields = {}
    _version: int
    _listeners: list[Callable[[], None]]

    ## Increment the structural generation and notify current listeners.
    ## 递增结构代次并通知当前监听者。
    #
    #  @return None
    def _notify(self):
        self._version = getattr(self, '_version', 0) + 1
        for callback in tuple(getattr(self, '_listeners', ())):
            callback()

    ## Subscribe once to changes in indexed collections.
    ## 对索引集合的变更订阅一次通知。
    #
    #  @param callback Consumer invalidation callback.
    #  @return None
    def watch(self, callback):
        if not hasattr(self, '_listeners'):
            self._listeners = []
        if callback not in self._listeners:
            self._listeners.append(callback)

    ## Subscribe to nested fact structures when inserted.
    ## 插入嵌套事实结构时订阅其变更。
    #
    #  @param value Inserted value.
    #  @return None
    def _adopt(self, value: object) -> None:
        if isinstance(value, FactStructure):
            value.watch(self._notify)

    ## Wrap versioned fields and notify replacement of their collection.
    ## 包装受版本跟踪的字段，并通知集合替换。
    #
    #  @param name Attribute being assigned.
    #  @param value New attribute value.
    #  @return None
    def __setattr__(self, name, value):
        collection = self._versioned_fields.get(name)
        if collection is not None:
            value = collection(value, changed=self._notify, adopt=self._adopt)
        object.__setattr__(self, name, value)
        if collection is not None:
            self._notify()

    ## Current structural generation; reading it does not scan children.
    ## 当前结构代次；读取时不遍历子项。
    #
    #  @return Current generation number.
    @property
    def version(self):
        return getattr(self, '_version', 0)
