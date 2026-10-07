## @package unstable_imports
#  Global import aliases are resolved only while their caller bindings hold.

import provider as engines
from provider import External as Remote

Remote = unknown_factory()
engines = unknown_factory()


def select_alias():
    return Remote


def select_module():
    return engines.External
