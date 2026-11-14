## @package tests.flow_test_support
#  Patch proof limits at the component that owns each implementation.
#  在拥有实现的组件上调整证明预算。
import pcresolve.flow.analysis.proof_context as proof_context
import pcresolve.flow.index.definitions as definitions


def set_class_binding_limit(monkeypatch, value):
    ## Set class-binding limits in each component that consumes them.
    ## 设置所有使用类绑定上限的组件。
    #
    #  @param monkeypatch pytest fixture or scoped patch context.
    #  @param value Maximum class-binding scan steps.
    #  @return None.
    monkeypatch.setattr(definitions, '_CLASS_BINDING_NODE_LIMIT', value)
    monkeypatch.setattr(proof_context, '_CLASS_BINDING_NODE_LIMIT', value)


def set_decorator_effect_limit(monkeypatch, value):
    ## Set decorator-effect limits in proof preparation.
    ## 设置证明准备阶段的装饰器效果上限。
    #
    #  @param monkeypatch pytest fixture or scoped patch context.
    #  @param value Maximum decorator-effect steps.
    #  @return None.
    monkeypatch.setattr(proof_context, '_DECORATOR_EFFECT_NODE_LIMIT', value)


def set_context_protocol_limit(monkeypatch, value):
    ## Set context protocol limits in proof preparation.
    ## 设置证明准备阶段的上下文协议上限。
    #
    #  @param monkeypatch pytest fixture or scoped patch context.
    #  @param value Maximum context protocol steps.
    #  @return None.
    monkeypatch.setattr(proof_context, '_CONTEXT_PROTOCOL_NODE_LIMIT', value)
