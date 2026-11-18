## @package pcresolve.flow.model.results
#  Public experimental value-flow result models.
#
#
#  Defines function selectors, call records and analysis snapshots consumed by
#  flow queries and serialization. These records use the experimental contract.
#  定义供数据流查询和序列化使用的函数选择器、调用记录及分析快照，遵循实验性契约。



import os
from dataclasses import dataclass, field, asdict

from pcresolve.flow.query.return_paths import trace_parameter


## A source function selector; definition location disambiguates duplicates.
## 源码函数选择器；定义位置用于区分重复名称。
@dataclass(frozen=True)
class FunctionRef:
    module: str = ''
    qualname: str = ''
    file_path: str = ''
    lineno: int = 0


## A source call or identified implicit protocol call, with source candidates.
## 带有源码候选项的调用或已识别隐式协议调用。
@dataclass
class FlowCall:
    id: str
    caller: FunctionRef
    callee_name: str
    lineno: int
    col_offset: int
    end_lineno: int = 0
    end_col_offset: int = 0
    target: object = None
    target_candidates: list = field(default_factory=list)
    parameter_bindings: list = field(default_factory=list)
    parameter_flows: list = field(default_factory=list)
    return_flows: list = field(default_factory=list)
    argument_sources: list = field(default_factory=list)
    argument_flows: list = field(default_factory=list)
    capture_bindings: list = field(default_factory=list)
    return_dependencies: list = field(default_factory=list)
    receiver_sources: list = field(default_factory=list)
    receiver_type_evidence: list = field(default_factory=list)
    callable_instance_evidence: dict = field(default_factory=dict)
    decorator_identity_evidence: list = field(default_factory=list)
    analysis_status: str = 'analyzed'
    target_status: str = 'definition_unavailable'
    mutation_flows: list = field(default_factory=list)
    effects: list = field(default_factory=list)
    result_sources: list = field(default_factory=list)
    binding_status: str = 'unavailable'
    binding_issues: list = field(default_factory=list)
    callable_sources: list = field(default_factory=list)
    analysis_contexts: list = field(default_factory=list)
    conditional_returns: list = field(default_factory=list)
    class_method_bindings: list = field(default_factory=list)
    constructor_bindings: list = field(default_factory=list)
    instance_method_bindings: list = field(default_factory=list)
    implicit_protocol: dict = field(default_factory=dict)
    class_metadata_bindings: list = field(default_factory=list)
    class_read_bindings: list = field(default_factory=list)
    conditional_source_bindings: list = field(default_factory=list)
    candidate_paths: list = field(default_factory=list)
    conditions: list = field(default_factory=list)


## An immutable-by-convention analysis snapshot with JSON-safe views.
## 按约定不可变且提供 JSON 安全视图的分析快照。
@dataclass
class FlowAnalysis:
    entry: FunctionRef
    inputs: dict
    functions: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    boundaries: list = field(default_factory=list)
    schema_version: str = 'flow-0.2'

    ## Find calls by caller and exact syntactic callee spelling.
    ## 根据调用方和精确语法调用名查找调用。
    #
    #  @param caller Optional function selector.
    #  @param callee_name Optional exact spelling.
    #  @return Matching calls in deterministic source order.
    def find_calls(self, caller=None, callee_name=None):
        return [c for c in self.calls
                if (caller is None or _matches(c.caller, caller))
                and (callee_name is None or c.callee_name == callee_name)]

    ## Return evidence for one exact call site.
    ## 返回单个精确调用点的证据。
    #
    #  @param call_id Identifier returned by find_calls.
    #  @return JSON-safe call flow record.
    def describe_call_flow(self, call_id):
        for call in self.calls:
            if call.id == call_id:
                return asdict(call)
        raise KeyError(call_id)

    ## Serialize the snapshot without internal AST objects.
    ## 序列化快照，不包含内部 AST 对象。
    #
    #  @return Dictionary suitable for json.dumps.
    def to_dict(self):
        return asdict(self)

    ## Trace an entry parameter through explicitly expanded return summaries.
    ## 通过显式展开的返回摘要追踪入口参数。
    #
    #  @param parameter Entry parameter name.
    #  @return Proven return paths and boundaries; absence is not a no-flow proof.
    def trace_parameter(self, parameter):
        return trace_parameter(self, parameter, FunctionRef)


## Match a function identity against optional selector components.
## 按选择器中提供的字段匹配函数标识。
#
#  @param actual Actual function identity.
#  @param selector Requested function selector.
#  @return True when all specified fields match.
def _matches(actual, selector):
    return (actual.qualname == selector.qualname
            and (not selector.module or actual.module == selector.module)
            and (not selector.file_path or actual.file_path == os.path.abspath(selector.file_path))
            and (not selector.lineno or actual.lineno == selector.lineno))



# Preserve the historical public class path for pickle compatibility.
for _public_type in (FunctionRef, FlowCall, FlowAnalysis):
    _public_type.__module__ = 'pcresolve.flow.analyzer'
del _public_type
