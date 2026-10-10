# PCResolve 性能瓶颈评估（2026-10-10）

评估基线：`25e58e21df14c24a2ade5646cdffdd90c13abfa7`，上游 PR #30 合并后的代码。这里保存评估脚本、结果摘要和优化建议；没有修改 `src/`、公共契约或分析预算。

这是修改前的评估；三项优先优化的实现与复测见
[后续优化报告](../performance-optimizations/README.md)。

主要瓶颈是 ownership 的重复候选证明与全表扫描，以及大源码集合上 value-flow 的重复建索引。8 个历史 pandas 切片均完成，但完整 pandas 和仓库自身的 ownership 分析仍未在 180 秒内完成。最值得先做的是参数反向索引、`__call__` 候选复用和源码版本级 flow 索引；空实参短路属于局部改进，不能解决历史 timeout 组。

## 测量范围与方法

- 复测 test1 的 8 个 pandas 批次，分别测量扫描、源码读取/解析、单文件访问、4 个结果绑定阶段、跨文件解析、调用归属、符号来源解释、结果组织、JSON 视图/编码/写入。
- value-flow 查询 `Index.append` 和 `Window.sum`，覆盖深度 1、3、5、单文件、20 文件组合、493 文件完整源码；同一分析器执行两次，每个入口参数在每份快照上查询两次。
- 对 ownership 的空实参路径做进程内 monkeypatch 消融实验，不修改生产实现。对照使用 `PYTHONHASHSEED=0`，原版和实验版都分别测首次、同实例再次分析；完整 JSON 指纹用于检查观测输出。
- Windows 11、Anaconda Python 3.13.9、Intel i5-1130G7、8 个逻辑核。本机结果不是原 Linux/Python 3.6 服务器的绝对时延承诺。源码只被静态解析，没有安装或执行旧 pandas。
- 同时记录 wall time 与进程 CPU time。CPU 计时分辨率约 15.625ms，小样本的零值并不代表免费。首次指分析器缓存为空，不代表清空操作系统文件缓存。
- 分阶段探针也有少量开销；cProfile/证明预算探针另跑，只用来定位热点，不把其时间当成正常运行时延。累计时间存在嵌套，不能把 profile 热点相加。
- 8 批初测使用解释器默认 hash seed；消融、范围测试和大批 profile 固定 seed 0。另对 normal 试验 seed 0/1/42，关键函数调用次数和完整 JSON 指纹一致；插桩 CPU 时间却为 13.4/24.8/28.9s，不能将该差异归因于算法工作量或 hash seed。本机环境状态未被隔离，数据用于定位瓶颈而非发布稳定百分比加速承诺。
- 工作集/峰值工作集来自 Windows 进程计数器，不是 `tracemalloc` 的 Python 分配量。重复分析后仍可能保留上一份结果，峰值增长不能据此认定内存泄漏。
- ownership 探针生成完整 JSON 并用 `write_text(payload + '\n')` 写出；写入阶段的临时字符串和换行转换会影响峰值，不能直接视作默认文本 CLI 的峰值。JSON 大小为 UTF-8 payload 大小，不含 Windows 换行转换。表中 ownership 文件数不包括兼容规则省略的根 `__init__.py`。
- 原有 `scripts/perf_baseline.py` 在 `tracemalloc` 开启时计时、没有阶段和重复数据，适合观测分配量；其绝对时间不可直接与本报告比较。

原始数据位于 `%TEMP%/pcresolve-performance-audit/`；紧凑结果保存在 [results.json](results.json)，所有数字表见 [tables.md](tables.md)。初次 flow 范围试验错误地选用了不包含 `Index.append` 的 timeout 切片，返回入口不存在；已改为显式加入 `base.py` 的 20 文件组合。那三次入口错误不计入性能结果。

## Ownership：先区分分析与输出

8 个历史批次均完成；本轮基准最慢的是历史 timeout 组，分析 wall 108.132 秒、CPU 105.047 秒，含解释器启动和完整输出的外部进程耗时 111.436 秒。

| 样本 | 分析 CPU | 单文件访问 | 调用归属 | 符号来源解释 | 主要现象 |
|---|---:|---:|---:|---:|---|
| step2-2-normal | 5.250s | 1.453s | 0.891s | 2.188s | 热点比较分散 |
| step2-2-longest | 45.125s | 1.734s | 2.391s | 39.562s | provenance 占约 88% |
| step2-2-timeout | 105.047s | 5.281s | 31.359s | 54.766s | 两种归属证明阶段合计约 82% |
| step2-3-longest | 12.953s | 0.938s | 0.797s | 10.594s | provenance 占约 82% |

timeout 组的 `_bind_bounded_local_call_results` 还消耗 11.016 秒 CPU。相比之下，读取/解析仅 0.344 秒，完整 JSON 的视图、编码和写入共 2.281 秒 CPU。只优化读取、JSON 或并行解析，不能解决这一组的主瓶颈。

### 已定位的重复工作

**大批次的首要热点：`__call__` 退回全边候选。** `project_call_context.py:150` 对 `__call__` 返回所有项目 edges；`_collect_project_edge_arguments` 每次查询一个参数都会逐个重新匹配。这是为保留任意语法拼写的 callable instance 而采用的保守路径，当前名字索引对它没有过滤作用。

step2-2-longest 仅 4,790 个调用点，profile 却记录了 **2,807,491 次** `_edge_targets_local_function`、2,750,776 次 `_callable_instance_targets_method`、2,755,829 次 `_local_callable_class_candidates`、3,589,152 次 `_local_class_from_source`。完整分析 profile 总计约 2.51 亿次函数调用、186.535s（有额外插桩）；`_collect_project_edge_arguments` 累计 145.921s，provenance 阶段 164.842s。

预算探针记录约 **259 万个独立 edge-target 根查询**，但只有 **7 个独立证明预算耗尽**。这里“根查询”是最外层被 `bounded_ownership_query` 包裹的调用；外部参数收集循环可以连续发起很多次根查询，每次重新取得预算。这直接说明该组主要是重复、数量庞大的短证明，不是少数递归证明一直撞预算。增加递归限额或只处理预算耗尽，无法解决其主体成本。

优化应围绕 callable-instance 候选和反向调用关系：按事实版本复用已证明的局部类身份/候选，保留不确定候选桶，避免同一目标的每个参数再次扫描所有边。先缓存只依赖固定 class 图的 `_local_class_from_source` 字符串身份解析和 `_local_target_metadata`，风险相对较低；更深的 callable class 答案依赖 receiver、parameter、visited、预算和符号改写，需要分层失效。**不能仅按名字把 `__call__` 的候选删掉**，否则 `f(...)`、别名、继承和注入的 callable 字段会漏报。

**历史 timeout 组的首要热点不同：参数签名全表扫描。** 该组 profile 总计约 2.40 亿次函数调用、207.421s。`_trace_parameter_source` 调用 **143,756 次**，自身 29.669s、累计 68.458s；其中 **49,731,113 次 `list.index`** 来自这个函数，耗时 37.780s。源码每次按参数名扫描所有函数，再用异常处理跳过不含该参数的签名。预建参数名反向索引，保留原函数顺序和首个位置，是该组最直接、风险相对低的改进。

该组还包括 `_local_class_from_method_result` 9,290 次、累计 24.874s，`_is_import_origin` 103,894 次、累计 23.143s，目标判定 811,065 次。预算耗尽的独立根查询共 **442** 个，包含触及深度上限的情况；不能把整个耗时归结为这些 cutoff。累计时间可能相互包含；特别不能将 68.458s 再加上它内部的 37.780s。

1. **空实参仍进行逃逸证明。** `project_local_classes.py:428` 取得 `arguments` 后，无论是否为空都调用 `_callable_field_receiver_escapes`。该函数按查询重建整模块 AST 调用位置表，随后再扫描 AST 查别名，并扫描模块调用边。空参数时，后面的候选循环不会进入，调用方最终仍返回 `[]`。可以先短路这一明确无候选路径。实验只在这一处跳过扫描，后续正式修复仍需要回归验证；部分路径可能因此少消耗证明预算，不能仅凭局部推理承诺全部项目输出恒等。
2. **局部 class/method 和参数名查询仍有全表扫描。** `_local_class_from_method_result` 遍历项目 class/method；`_trace_parameter_source` 遍历函数签名并反复 `params.index`。可分别建立末级方法名候选索引、参数名到原序 `(函数, 首个位置)` 列表。保留候选顺序、别名检查和调用点的实时读取，不能简单改成“同名方法就是目标”。
3. **import 来源判定每次扫描符号。** `_is_import_origin` 扫描 `symbols.direct` 以及 import 类型的 `symbol_refs`，进行双向点分隔前缀匹配。可索引已有字符串和祖先前缀，但前四个结果绑定阶段会改写符号；必须按事实版本失效，或只在事实稳定后建立索引。
4. **同类证明在多个输出阶段重复。** `get_calls` 与 `_build_symbol_provenance` 都会进入来源、receiver、返回值解析。当前每个最外层受装饰器保护的查询共享最多 4096 个查询入口、深度 32 的预算；它不限制每个查询内部的 AST/边扫描，也不限制外部循环发起根查询的总次数。因此“有环检测、有预算”仍不等于大项目有固定总时限。

普通组在当前合并代码的现有 cProfile 中：`_callable_field_receiver_escapes` 76 次、累计 2.823s；`_is_import_origin` 11,949 次、1.146s；`_local_class_from_method_result` 1,228 次、0.638s；`_trace_parameter_source` 5,120 次、0.691s。这是插桩时间，函数间可能嵌套。普通组的数据不能直接代表 timeout 组。

### 空实参消融结果与计时噪声

4 个对照样本、每个版本两次分析，完整 JSON 指纹全部一致。两次合计跳过的逃逸扫描次数分别为：step2-2-longest **2088**、normal **96**、timeout **0**、step2-3-longest **0**。所以短路能消除部分批次的明确冗余工作，但**不会解决历史 timeout 组**。

计时不能全部归因于实验：longest 的首次/再次 CPU 从 53.219/52.828s 变为 48.797/44.766s；但零命中的 step2-3-longest 也从 8.859/10.203s 变为 7.938/7.344s，零命中的 timeout 再次分析反而从 79.094s 增至 89.859s。固定 hash seed、串行运行仍不能消除本机计时波动。该实验提供“跳过哪些工作、样本输出是否一致”的证据，**不足以承诺稳定百分比加速**。后续正式性能门槛应交错执行多轮新进程对照，同时保留函数调用次数、预算消耗和输出一致性。

补充 GC 探针：normal 的三次分析 wall 为 15.262/9.681/11.295s，GC 回调累计为 0.141/0.232/0.280s，占各次分析约 0.9%/2.4%/2.5%。该样本的主要成本不是垃圾回收；这不能外推到 493 文件完整源码的 GC 占比。三次输出指纹一致，大批次 cProfile/预算插桩输出也与对应原版消融输出一致。

缓存应优先保存静态候选、签名、AST 位置和作用域事实。`visited`、接收者、入边、实参、预算状态影响证明结果；按函数名做全局结果缓存会产生错误复用，尤其不能把预算耗尽结果永久缓存为“没有流/没有候选”。

## 更大范围与非 pandas 样本

- 单独 `pandas/core/indexes/base.py`：1 个模块、1,030 个调用，ownership 分析 wall **2.721s** / CPU **2.719s**；诊断 0。本轮未复现最初报告中的 RecursionError。
- `allnews` 项目：1,013 个调用，分析 wall **2.980s** / CPU **2.938s**，诊断 0；用于检查并非所有千级调用样本都耗时很长。
- 完整 pandas 0.21.0：493 个 `.py` 文件，包含 tests。进程在 **180 秒截止时仍未完成**，停留在 `_bind_bounded_local_call_results`，尚未进入 get_calls/provenance。读取解析约 **6.621s**，源码快照后 RSS **547.2 MiB**；约 58.4s 完成各文件 visit 时 RSS 已 **1101.6 MiB**，这是完成事件记录到的下界，未取得最终峰值。
- 当前 `src/pcresolve`：54 个 `.py` 文件、约 1.06 MiB 源码；进程也在 **180 秒截止时未完成**，约 22.4s 进入 `_build_symbol_provenance` 后一直未返回。这说明来源解释的扩展性问题不局限于 pandas。这里没有取得完整结果，不报告最终调用数或诊断数。

整库的重型结果绑定与内存容量问题仍然存在；8 个切片全部完成不能外推成整库可在 180 秒内完成。两次整项目测试是有意设置上限的删失观测，不把它们记为“180 秒分析完成”，也不估算未完成总时长。大项目的内部函数级 profile 尚未跑完，具体绑定阶段的细分占比不能直接套用切片结果。

## Value-flow：输入范围与重复索引是当前大头

同样选择 `Index.append`、深度 3：

| 可用源码 | 首次分析 wall | 其中 index | 同实例再次分析 | 其中 index | 展开函数/调用 |
|---|---:|---:|---:|---:|---:|
| 仅 base.py | 0.111s | 0.070s | 0.074s | 0.032s | 3 / 13 |
| base.py 加 timeout 切片，共 20 文件 | 0.575s | 0.549s | 0.269s | 0.242s | 3 / 13 |
| 完整 pandas，共 493 文件 | 13.510s | 12.989s | 4.549s | 4.077s | 5 / 31 |

扩大输入可提高定义覆盖，展开函数数也会不同；这些范围不是语义等价的替代方案。`import_roots` 只参与模块命名，不会自动补充源码。

`FlowAnalyzer.__init__` 只扫描/登记文件，实际成本在每次 `analyze()` 的 `_index()` 中：重新读取整个文件集合，复用内容未变的 AST，但重建 definitions、classes、imports、module bindings 和 definition index，清空 scope/return/effect/context 等缓存。当前没有公共 `AnalysisSession`，ownership 与 flow 分别持有状态，不能假设它们跨分析共享缓存。

完整源码、深度 3 的 cProfile：总 24.810s，`_index` 23.388s；`collect_lambdas` 1,736,893 次调用、累计 11.514s；SourceStore snapshot 7.862s；DefinitionIndex 构造 1.688s；`_reachable_modules` 0.826s。这里首要候选是**基于源码内容版本复用中立索引**，然后才是优化 AST 遍历和模块前缀检索。每个 imported name 都重新排序 known modules 可以先把排序提到循环外；仍需保留最长模块前缀匹配。

深度确实增加摘要成本：单文件 `Window.sum` 首次 analyze 从深度 1 的 0.031s，增至深度 3 的 0.186s、深度 5 的 0.208s；调用从 2 增至 68、80。完整源码 `Index.append` 深度 1/3/5 为 13.149/13.510/15.305s，输入建索引仍占主要成本。未解析边和深度边界会截断展开；这些结果不能证明任意深度、任意库都这么快。

`FlowAnalysis.trace_parameter` 每次重建 ReturnCall/binding，再对全部展开函数重新执行返回摘要固定点（默认最多 32 轮、每函数 2048 依赖），最终才筛选参数。在本次真实样本里是毫秒级，重复查询的缓存有价值，但应排在索引复用之后。快照“约定不可变”而非强制冻结；若缓存返回闭包，需要明确快照变更/失效策略，并保留 converged/bounded、unknown 和所有 boundaries。

调用方可先复用一次 `analyze` 得到的快照查询多个调用点和参数。实参到形参的转发关系已经在 call records 中，可用 `find_calls`/`describe_call_flow`；`trace_parameter` 查询的是入口参数到展开后返回值的关系。只需要 value-flow 的工作流可以直接使用 FlowAnalyzer，无须先做完整 ownership；但当前没有业务查询脚本，不能断言现有调用方重复执行了这两步。减少可用源码范围要同时检查 definition_unavailable 等边界，不能把更快但覆盖更少的结果当成等价优化。

`_merge_summary` 顺序寻找已有调用、`_unique` 用列表等值去重，存在宽图下的二次增长风险。本轮未证明它们是主要热点，列为后续大上下文压力测试候选，不直接给出速度承诺。

## 输出、内存及扫描

完整 ownership 输出保留文件级与项目级 API calls/provenance，`build_full_view` 会两次生成对应字典；`_relpath` 为每条记录重复转换文件路径。普通组的 profile 中 relpath 16,571 次、累计 0.958s。可按 `(path, root)` 缓存路径，或在保留 schema 的前提下复用内部转换结果；要注意返回字典别名是否改变可变视图的使用行为。

timeout 组 JSON 为 23.48 MiB，探针运行峰值 RSS 251.2 MiB；分析结束 RSS 127.9 MiB、构建视图后 155.5 MiB、编码阶段峰值 189.3 MiB，写出阶段峰值继续增加。该数值含探针的写法，不是默认文本 CLI 的峰值。分析结果、视图、字符串物化阶段同时存在多份对象。流式输出有望降低峰值，但要保留 JSON 契约；它对该批次的主分析时延帮助有限。该组 summary 仅 29,087 字节，但 `--json-summary` 仍先执行完整 `analyze_project`；`--top` 也不限制分析范围。

summary 的 symbol_count/library_usage 仍依赖 provenance，不能简单跳过该阶段并宣称兼容。现有 full schema 的重复字段也不能为省内存直接删除。

`_build_file_analysis` 按每个文件过滤全部 provenance，是 O(文件数 × provenance 数)；可以按 file_path 一次分桶。当前 18 文件 timeout 组该阶段仅 0.125s CPU，不是第一优先级。源码/AST 缓存按分析器持有；同实例重复分析会重新构建大量状态，因此不能把 AST 命中率当作整个分析的复用率。

扫描器是在遍历完成后过滤非隐藏虚拟环境目录；含大 venv 的真实目录可能额外付出遍历成本。当前 pandas 切片没有这种目录，扫描耗时很小，这条属于代码审计发现，尚未用含 venv 的数据实测。`followlinks=True` 的链接目录行为也应单独测试，不以本次数据推断。

## 建议实施顺序与验收

| 顺序 | 改动 | 支撑证据 | 风险/边界 |
|---|---|---|---|
| 1 | 参数名 → 原序函数/位置反向索引 | timeout 的 4,973 万次签名 `list.index` | 保留首个参数位置、函数顺序、实时 call_sites；不能按参数名猜函数作用域 |
| 2 | `__call__` 候选及反向调用复用；先复用纯 class 身份和 target metadata | longest 的 281 万次目标判定，约 259 万独立根查询 | 动态 callable、继承、别名和字段注入必须保留；按事实版本失效 |
| 3 | class/method 候选索引、import 来源前缀索引 | timeout 中分别 24.874s、23.143s 的累计 profile 时间 | 绑定 pass 会改写 direct/source，缓存需要失效；候选仍须做原有证明 |
| 4 | Flow 的源码版本级索引复用 | 493 文件查询首次约 13s、同实例仍约 4.5s，主要在 index | 源码、文件集合、import roots、读取策略和重名定义变化都要覆盖；查询语义缓存单独管理 |
| 5 | 空实参短路、AST 调用位置表复用 | longest 每次可少做 1044 次逃逸扫描；timeout 命中 0 | 易做局部改进，但不是最慢组的主要方案 |
| 6 | 路径转换缓存、provenance 按文件分桶、输出内存改进 | 完整 JSON 的重复视图和内存峰值；分析 CPU 占主导 | 保持 ownership schema 和视图可变行为兼容 |
| 7 | 每快照共享返回依赖闭包、宽图去重/merge 索引 | trace_parameter 重复固定点；当前样本仅毫秒级 | 快照可变性、上下文/条件/边界、预算状态必须保留；先增加压力样本 |

第 4 项在“对同一大源码集合查询大量入口”的业务中可提前，与 ownership 优化独立推进。前两项对应不同慢样本，应分开落地、分别验证，避免一个普通样本的加速掩盖另一个大批次的退化。

验收保持相同源码集合、查询入口、预算、候选顺序和 boundary 语义，比较完整 JSON、调用数、函数/调用上下文数及 budget 消耗。ownership 实现变更需要相关 fixture、完整 pytest、ground-truth/release gate；flow 变更需要相关 fixture、严格 value-flow matrix、完整 pytest；共享事实层变化同时覆盖两侧。本轮是评估和实验探针，没有修改实现，因此没有把旧轮次的测试结果当成本轮通过记录。

后续性能门槛应将正常计时、cProfile、内存分配追踪分开；固定 hash seed，交错执行至少多轮 fresh-process 对照，记录中位数/分位数、CPU、峰值、结构性调用次数与完整输出。冷/暖分析分别报告，不把两者平均后称为同一种运行。

## 复现

```powershell
python reports/performance-audit/run_matrix.py batches
python reports/performance-audit/run_matrix.py controlled
python reports/performance-audit/run_matrix.py profiles
python reports/performance-audit/run_matrix.py scope
python reports/performance-audit/run_matrix.py small-probes
python reports/performance-audit/run_flow.py
python reports/performance-audit/collect_results.py
```

上述批量驱动使用 `%TEMP%/pcresolve-pandas-batch-repro` 的现有复现数据；换机器时需调整数据路径。通用 `ownership_probe.py SOURCE --out DIR` 和 `flow_probe.py --source FILE --import-root ROOT --entry MODULE:QUALNAME --output REPORT.json` 可以独立使用。完整输出、stderr、事件日志和 profile 保存在原始数据目录。
