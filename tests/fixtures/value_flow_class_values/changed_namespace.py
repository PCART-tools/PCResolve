## @package changed_namespace
#  A write through an imported module can change its exported class identity.

import provider as engines

engines.External = unknown_factory()


def select():
    return engines.External
