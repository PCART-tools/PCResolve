## @package tests.fixtures.parameter_receiver_ownership.dispatch
#  Cross-file virtual-dispatch fixtures.


class CrossFileDispatchBase:
    def apply(self, value):
        return self._apply(value)


class CrossFileJsonDispatch(CrossFileDispatchBase):
    def _apply(self, value):
        value.object_hook({})
