import targets as api
import builtins as bi


def change():
    alias = api.GlobalWrite
    setattr(alias, 'generate', unknown_callable)


def builtin_alias_change():
    bi.setattr(api.BuiltinAliasWrite, 'generate', unknown_callable)


def conditional_alias_change(flag):
    alias = api.BranchWrite
    if flag:
        alias = api.BranchOther
    alias.generate = unknown_callable
