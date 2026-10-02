## @package consumer
#  Function-local import bindings take precedence over caller method names.


class Owner:
    def together(self, *args, **kwargs):
        from exports import together
        return together(self, *args, **kwargs)

    def aliased(self, *args, **kwargs):
        from exports import together as simplify
        return simplify(self, *args, **kwargs)

    def reexport_alias(self, *args, **kwargs):
        from exports import joined as simplify
        return simplify(self, *args, **kwargs)

    def module_alias(self, *args, **kwargs):
        import exports as algorithms
        return algorithms.together(self, *args, **kwargs)

    def imported_class_member(self, *args, **kwargs):
        from consumer import Owner as Klass
        return Klass.aliased(self, *args, **kwargs)

    def module_alias_before_write(self, replacement, *args, **kwargs):
        import exports as algorithms
        result = algorithms.together(self, *args, **kwargs)
        algorithms.together = replacement
        return result

    def module_attribute_rebound(self, replacement, *args, **kwargs):
        import exports as algorithms
        algorithms.together = replacement
        return algorithms.together(self, *args, **kwargs)

    def later_rebind(self, replacement, *args, **kwargs):
        from exports import together
        result = together(self, *args, **kwargs)
        together = replacement
        return result

    def rebound(self, replacement, *args, **kwargs):
        from exports import together
        together = replacement
        return together(self, *args, **kwargs)

    def conditional_missing(self, flag, *args, **kwargs):
        if flag:
            from exports import together
        return together(self, *args, **kwargs)

    def conditional_targets(self, flag, *args, **kwargs):
        if flag:
            from exports import together
        else:
            from exports.leaf import other as together
        return together(self, *args, **kwargs)

    def for_missing_binding(self, items, *args, **kwargs):
        for item in items:
            from exports import together
        return together(self, *args, **kwargs)

    def while_missing_binding(self, flag, *args, **kwargs):
        while flag:
            from exports import together
            break
        return together(self, *args, **kwargs)

    def cyclic(self, *args, **kwargs):
        from cycle_a import together
        return together(self, *args, **kwargs)

    def reassigned_export(self, *args, **kwargs):
        from reassigned_export import together
        return together(self, *args, **kwargs)

    def ambiguous_export(self, *args, **kwargs):
        from ambiguous_export import together
        return together(self, *args, **kwargs)

    def conditional_export(self, *args, **kwargs):
        from conditional_export import together
        return together(self, *args, **kwargs)
