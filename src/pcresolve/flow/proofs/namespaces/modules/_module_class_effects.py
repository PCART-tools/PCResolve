## @package pcresolve.flow.proofs.namespaces.modules._module_class_effects
#  Compatibility entry point for module class-effect proofs.

from pcresolve.flow.proofs.classes._class_creation_calls import creation_calls
from pcresolve.flow.proofs.namespaces.modules._module_class_effects_core import module_class_effects as _evaluate


## Evaluate module class effects using the standard class-creation proof.
#  @param analyzer Fixed source generation and budgets.
#  @param target Exact source root-class declaration.
#  @param call Standalone module-level classmethod call.
#  @return Phase-specific effects or None.
def module_class_effects(analyzer, target, call):
    return _evaluate(analyzer, target, call, creation_calls)
