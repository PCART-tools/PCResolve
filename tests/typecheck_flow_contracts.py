## @package tests.typecheck_flow_contracts
#  Static type probes for cross-component flow callbacks.
#  数据流跨组件回调的静态类型检查用例。

from pcresolve.flow.analyzer import FlowAnalyzer
from pcresolve.flow.contracts import FreshDecorationProvider


## Confirm that the analyzer callback satisfies the proof-provider contract.
## 确认分析器回调符合证明提供者契约。
#
#  @param analyzer Configured flow analyzer.
#  @return Provider accepted by proof construction.
def fresh_decoration_provider(analyzer: FlowAnalyzer) -> FreshDecorationProvider:
    return analyzer._fresh_decoration_fact
