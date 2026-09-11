# Value-flow 评估与测试

最初对 `b1545c2` 的值流实现建立了扩展评估矩阵，当时未修改分析器。
矩阵覆盖 **83 个入口案例、472 个检查**；历史基线中 421 项符合预期，51 项暴露已知缺口，
分布在 21 个入口案例中。51 是失败检查数，同一问题可能影响绑定和多条值流，不能视为 51 个独立缺陷。

按该矩阵完成增强后，当前报告为 **472/472 全部符合预期**，`tests/value_flow_known_gaps.json`
已清空。矩阵已参与修复，因此该结果只表示这些已知语义和边界的回归覆盖，不是独立留出集精度。

查看[历史基线报告](value-flow-matrix-baseline.md)、[历史基线 JSON](value-flow-matrix-baseline.json)、
[当前逐项报告](value-flow-matrix-current.md)和[当前 JSON](value-flow-matrix-current.json)。
上一轮的[12 个开发案例](value-flow-evaluation.md)和历史基线继续保留。

## 范围与预期的来源

| 分组 | 入口数 | 重点 |
|---|---:|---|
| binding | 24 | 位置/关键字/default/variadic 参数、解包、别名/重导出、receiver、descriptor、继承、覆盖、super、装饰器 |
| control | 25 | 覆盖赋值、分支、短路、循环、异常、finally、闭包、nonlocal、lambda、递归、async、generator |
| containers | 25 | 索引/切片、字典键值/覆盖、别名、循环引用、append/clear/pop、跨调用修改、推导式 |
| contract | 5 | 输入文件集合、depth、函数数量预算、调用数量预算与边界 |
| stdlib | 4 | CPython `_splituser`、`_splitvalue`、`_splitnport`、`_get_sep` 的原始函数片段 |

每个项目的 `manifest.json` 固定入口、显式文件集合或项目根、深度、预期关系和语义理由。
标准库字符串案例还显式提供已复核的 `str` 参数形状；分析器不会仅凭三元解包猜测接收者类型。
Gold 先按源码语义编写，再运行分析器；没有将当前输出反向改成预期。所用约定为：

- 判断正常执行中可能存在的显式值传播，包含派生值和容器内容；控制条件本身不算值流。
- `and`/`or` 可能直接返回条件操作数，此时该操作数确实存在值流。
- 方法案例采用 fixture 定义类的普通实例，排除 monkey patch 和额外子类；候选绑定的运行时覆盖假设仍记在诊断中。
- async 入口的返回指 await 后的函数体结果；未 await 的同步外层案例不会执行异步函数体。
- `next(generator)` 检查 yield 到消费者的路径，区别于生成器最终 `return`。
- callee 的返回端点可以是 `None`：`return values.append(x)` 有调用返回端点到入口返回的边，
  但没有 `x` 到入口返回的值流。
- 外部函数和未知 callback 的参数到返回关系不臆测；可以独立检查调用返回端点和源码缺失边界。

CPython 片段来自本机 Anaconda Python 3.13.9 的标准库，保留函数原文、版本、原文件/函数哈希及许可证，
见 `tests/fixtures/value_flow_matrix/stdlib/SOURCE.json`。它们是源码片段评估，不是整个 CPython 项目分析。
矩阵中的新 Python 源码使用 Python 3.9 兼容语法；本次实际运行环境是 Python 3.13.9，未声称已在 3.9 运行。

这是一套覆盖主要语义的开发评估，不是对所有 Python 语法和动态行为的穷尽证明。
只有四个标准库真实函数片段，不能据此推断所有真实项目的准确率；一旦用此矩阵指导修复，它也不再是留出集。

## 当前结果

| 维度 | 检查数 | 结果 |
|---|---:|---|
| 词法调用收集 | 82 | 82 符合 |
| 指定调用点存在 | 41 | 41 符合 |
| 调用目标 | 39 | 39 符合 |
| 实参/形参绑定 | 54 | 54 符合 |
| 显式参数流 | 65 | 45 正例找到，20 负例未报告路径 |
| 隐式 receiver 流 | 7 | 5 正例找到，2 负例未报告路径 |
| callee 返回到入口返回 | 41 | 34 正例找到，7 负例未报告路径 |
| 入口参数到入口返回 | 137 | 75 正例找到，62 负例未报告路径 |
| 边界契约 | 6 | 6 符合 |

## 历史基线结果分维度解释

| 维度 | 检查数 | 结果 |
|---|---:|---|
| 词法调用收集 | 82 | 81 符合，1 不符；有意限制调用预算的案例不参与全量收集检查 |
| 指定调用点存在 | 41 | 40 存在，1 缺失 |
| 调用目标 | 39 | 34 符合，5 未解析；包含预期无定义的控制项 |
| 实参/形参绑定 | 54 | 46 符合，8 未解析 |
| 显式参数流 | 65 | 37 正例找到，17 负例未报告路径，11 因绑定/调用缺失而未解析 |
| 隐式 receiver 流 | 7 | 4 正例找到，3 未解析 |
| callee 返回到入口返回 | 41 | 32 正例找到，7 负例未报告路径，1 正例遗漏，1 调用缺失 |
| 入口参数到入口返回 | 137 | 75 正例中找到 61、遗漏 14；62 负例中 56 未报告路径、6 报告错误路径 |
| 边界契约 | 6 | 全部符合 |

`negative_no_path` 只是该负例未观测到路径，不是分析器证明了无流。
当形参绑定未知时，相关参数流记为 `unresolved`，不会获得“负例通过”的信用。
分析或查询异常记为 `error`，所有计划检查保留在分母内；本轮没有分析异常。
每个结果还保留 target status、query status、固定点状态和边界原因。

没有给出单一总准确率：这些指标粒度不同、正负比例人为选择，且多个失败检查可能来自同一根因。

## 已完成的增强顺序

1. **先处理误报**：`*args`/`**kwargs` 元素选择、字典动态键及解包后的覆盖、跨调用 `clear`、`nonlocal` 写入后的旧值残留。
2. **修复调用点身份**：`super().echo(x)` 的内外调用共享起始行列，当前丢掉了外层调用；应以完整源码范围区分。
3. **补目标及绑定**：已知元组解包、未知 `*args` 后的独立关键字绑定、局部 callable 别名、staticmethod/classmethod、super、装饰器返回 callable。
4. **补传播与协议**：字典 key 内容、None 返回端点、pop、lambda、yield/next，以及有输入类型前提的字符串 partition/rpartition。

这些阶段已依次完成。它们消除了矩阵内的已知误报、遗漏和未解析绑定，
不表示动态类型边界均可消除。

## 复跑和生成报告

在仓库根目录、安装开发版包后运行：

```shell
python scripts/evaluate_value_flow_matrix.py --output matrix.json --markdown matrix.md
python scripts/evaluate_value_flow_matrix.py --strict
python -m pytest tests/test_value_flow_matrix.py tests/test_value_flow_matrix_runner.py tests/test_value_flow_contract.py -q
python -m pytest tests/ -q
```

默认评估命令记录缺口并正常退出；`--strict` 在任一未解析、误报、遗漏或异常时返回 1。
报告包含 Git revision、Python 版本、分析器/评估器哈希及所有 fixture/manifest 哈希。
`seconds` 是观测值，不是可移植性能阈值。

`test_value_flow_matrix.py` 根据 manifest 生成逐检查 pytest 参数；每个案例只分析一次并复用结果。
`tests/value_flow_known_gaps.json` 明确列出当前已知缺口的检查 ID、结果类型和原因；当前为空。
它只控制 pytest 的 `strict xfail`，评估器本身完全不读取这份清单。

- 已知失败仍执行；修复后成为 strict XPASS，要求移除对应条目。
- 新增未登记失败直接使测试失败。
- 已知失败变为异常或其他失败模式，也会被独立检查拦截，不能藏在 xfail 中。
- 不批量自动接受新的失败基线；必须先复查语义、输入范围和原因。

另外增加了 14 个接口契约用例，覆盖非法预算、显式文件/目录等价、文件新增/修改后的快照失效、
序列化隔离、重复定义选择、未知参数/调用、展开等价及可信摘要变化。
评估器自身有 10 个测试，覆盖异常分母、缺失调用/形参、默认参数/receiver、定义时调用、特殊调用字符串和报告展示。
既有 CLI、Unicode/多行 evidence、ownership 回归继续随完整测试执行。

历史基线完整回归记录为 **1,898 passed、51 xfailed、41 warnings**。
增强完成后的完整回归为 **1,977 passed、41 warnings**，无 xfail；这些 warnings 来自既有真实项目
fixture 的转义序列。另对新增 Python 文件执行 Python 3.9 语法解析检查。

## 后续扩展

下一组留出评估应从未参与修复的多个真实项目中抽样，固定源码 revision、入口签名、允许文件集合、
展开预算和人工复核关系。多重继承、动态 descriptor、一般 escaping heap、异常中的部分副作用、
协程调度和用户定义协议等仍未被本矩阵全面覆盖。
PCResolve 的主消费面仍是 API call ownership；值流评估与 ownership 评分分别报告。
