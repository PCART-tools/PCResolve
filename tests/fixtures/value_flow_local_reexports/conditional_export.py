## @package conditional_export
#  The exported callable depends on unknown module state.

if enabled:
    from exports.leaf import together
else:
    from exports.leaf import other as together
