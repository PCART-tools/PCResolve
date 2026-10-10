# PCResolve 三项性能优化与逐项评估（2026-10-10）

基线为 `25e58e21df14c24a2ade5646cdffdd90c13abfa7`。按
[修改前评估](../performance-audit/README.md) 的三个优先级实现优化。
稳定 ownership schema、experimental `flow-0.2`、证明深度和查询预算保持原契约。

## 1. 参数名反向索引

`SingleFileAnalyzer` 按参数名建立原序 `(function_name, first_index)` 列表；
`_trace_parameter_source` 只访问包含该参数的签名。继续实时读取调用点。
函数和 lambda 定义收集会使索引失效，下一次查询重新构建。
保留简单方法名被覆盖后的字典顺序、限定方法别名，以及重复名称的首个位置语义。

先加入复现测试：201 个签名上的三轮有效/缺失参数查询，旧实现执行 606 次
`list.index`；优化后为 0。另验证同名方法别名顺序、后续定义收集与调用点更新。

在只应用这一项修改时重跑历史 timeout 组：来自
`_trace_parameter_source` 的 `list.index` 调用从 **49,731,113 降到 0**。
该函数自身时间从旧 profile 的 29.669s 降到 0.215s，累计从 68.458s 降到
1.723s。两次 profile 的插桩配置与环境存在差异，因此这些时间用于定位，
不作为正常运行加速比。完整 JSON 与固定 seed 的修改前输出一致。

## 2. Callable 实例候选与反向调用关系

对不依赖递归参数证明的来源复用静态 callable 类候选；以这些候选建立
`__call__` 定义候选和反向调用边索引。候选只用于筛选，最终仍调用现有精确目标判定。
以下证据保留：任意名称的 callable 实例、别名、显式 `.__call__`、mapping targets、
继承，以及需要递归解析参数/字段的来源。继承类和参数字段保留全候选，
避免把预算耗尽或访问环得到的空结果缓存为否定结论。

callable 索引在边或模块符号绑定改写时失效；新 analysis 的 graph identity
防止跨运行复用。静态候选缓存不再在每次命中时重建整项目的边版本元组。
先加入无关调用边复现，再验证反向索引与全量匹配一致、重写后刷新、重复分析刷新。

两个慢组的完整 JSON 与原版一致。最长组的 profile 中目标判定从
**2,807,491 降到 225,408 次**，callable 类解析从 **2,755,829 降到 172,497 次**。
最终代码另行采集的 profile 确认了这些计数，完整 JSON 指纹与修改前一致。
最终最长组的 `_get_edge_lookup` 为 36,589 次，累计 0.833s；
静态候选缓存命中不再进行全项目边版本检查。

## 3. Flow 源码版本级索引复用

同一 `FlowAnalyzer` 在所选源码文档、源码集合、读取策略和有序 import roots
均不变时，复用 definitions、classes、imports、ModuleIndex 和 DefinitionIndex 等事实。
每次 analysis 仍读取内容，不能以 size/mtime 判断版本。只保留最新一代索引。

查询的 context、预算计数、返回/对象/effect 摘要和作用域缓存每次清空。
入口、深度、预算或 contract 变化不会复用旧查询结果，旧 FlowAnalysis 保持独立。
构建失败先撤销可复用标记，下一次查询不能命中部分构建的索引。

复现测试先确认旧版两次 query 会构建两次 DefinitionIndex；新版仅构建一次。
回归覆盖相同 size/mtime 的内容修改、增删文件、读取/语法失败及恢复、import roots
变化、预算、contracts 和结果对象隔离。

完整 pandas 493 文件的 `Index.append`、depth=3，同一分析器三次查询：

| 查询 | 旧版 analysis / index | 新版 analysis / index |
|---|---:|---:|
| 首次 | 14.694s / 14.356s | 13.728s / 13.365s |
| 第二次 | 3.509s / 3.112s | 0.453s / 0.080s |
| 第三次 | 3.984s / 3.507s | 0.411s / 0.059s |

六次完整 snapshot 指纹完全一致（5 functions、31 calls）。首次查询仍需全库索引，
本项主要改善同一分析器的后续查询，并没有让新的 CLI 进程直接命中缓存。

## 复测方法

所有性能进程串行运行，`PYTHONHASHSEED=0`；使用 Windows 11、Anaconda Python
3.13.9。Ownership 对两个慢组按旧版、新版、新版、旧版顺序运行独立进程。
另重跑八个历史切片，完整 pandas 和仓库自身保留 180s 进程截止。
profile 单独采集，正常运行时延与插桩时间不混用；两轮范围不代表服务器时延承诺。

两个慢组的 analysis 时延（不含视图、JSON 编码、文件写入）：

| 样本 | 旧版 wall，两轮 | 新版 wall，两轮 | 旧版 CPU，两轮 | 新版 CPU，两轮 |
|---|---:|---:|---:|---:|
| step2-2-longest | 53.974 / 61.183s | 15.107 / 16.933s | 50.484 / 58.047s | 13.906 / 16.125s |
| step2-2-timeout | 110.759 / 87.262s | 54.950 / 57.128s | 106.984 / 85.031s | 53.234 / 52.781s |

八次运行的完整 JSON 指纹按各自样本完全一致。时延存在环境波动，
但交错两轮均观察到改善，且有签名扫描/目标判定次数下降的独立证据。

八个历史切片在 180s 截止内全部完成，完整解析后的 JSON 与修改前均一致。
历史初测中 longest/timeout 两组未记录 hash seed，序列化的对象键顺序
与本轮不同；因此另保留原始 payload hash，并逐个比较完整 JSON 对象，
不会把数组重新排序或删除字段来消除差异。固定 seed 的上述交错对照中，
这两组直接按 payload hash 比较也全部一致。

| 历史切片 | 本轮 analysis wall / CPU | 调用数 | 诊断数 |
|---|---:|---:|---:|
| step2-2-longest | 17.562s / 17.188s | 4,790 | 0 |
| step2-2-normal | 3.921s / 3.859s | 2,987 | 0 |
| step2-2-shortest | 0.015s / 0.016s | 13 | 0 |
| step2-2-timeout | 41.203s / 41.000s | 8,395 | 0 |
| step2-3-error-window-sum | 0.429s / 0.406s | 621 | 0 |
| step2-3-longest | 4.421s / 4.391s | 1,551 | 0 |
| step2-3-normal | 0.392s / 0.391s | 546 | 0 |
| step2-3-shortest | 0.044s / 0.047s | 85 | 0 |

范围复测：

| 范围 | 结果 | 完成情况 |
|---|---|---|
| 单独 base.py | analysis 2.871s，1,030 calls，0 diagnostics | 正常完成 |
| allnews | analysis 2.829s，1,013 calls，0 diagnostics | 正常完成 |
| 完整 pandas，493 个源码文件 | 180s timeout | 尚在 `_bind_bounded_local_call_results`，analysis 未结束 |
| 仓库自身 | 180s timeout | 尚在 `_build_symbol_provenance`，analysis 未结束 |

完整 pandas 在约 72.8s 完成 visit 后进入结果绑定；仓库自身约 39.8s 进入
provenance。这些是阶段进展，并不是完成时延或最终内存峰值。
本轮三项优化没有解决这两个完整项目的 180s 限制，不能据此宣称全项目性能问题已解决。
后续应针对这些剩余阶段继续检查 class/method 返回来源的全表扫描、import 来源扫描、
参数字段逃逸的重复 AST 扫描，以及跨独立证明的重复工作；源码索引复用也不能加速首次 Flow 查询。

原始完整 JSON、阶段日志和 profiles 在 `%TEMP%/pcresolve-priority-results/`，
紧凑测量与 fingerprint 检查保存在 [results.json](results.json)。
逐项 profile 计数保存在 [profiles.json](profiles.json)，严格 Flow matrix 的
各项结果保存在 [value-flow-matrix.json](value-flow-matrix.json)。

复测驱动和收集脚本：

```powershell
python reports/performance-optimizations/evaluate.py --data <sources> --baseline <archived-baseline> --out <raw/group> --group paired
python reports/performance-optimizations/evaluate.py --data <sources> --baseline <archived-baseline> --out <raw/group> --group batches
python reports/performance-optimizations/evaluate.py --data <sources> --baseline <archived-baseline> --out <raw/group> --group scope
python reports/performance-optimizations/evaluate.py --data <sources> --baseline <archived-baseline> --out <raw/group> --group flow
python reports/performance-optimizations/collect.py --raw <raw> --audit <prior-audit> --output reports/performance-optimizations/results.json
```

基线目录由 `git archive` 构建，包含旧版 `src/` 和相同的两个测量探针。
不安装或执行被分析的 pandas 代码。

## 最终验证

- 新增 14 项回归/工作量测试，先复现三个问题再修改实现。
- 最终 `python -m pytest -q --disable-warnings`：**2545 passed**，44 条既有源码语法警告。
- 严格 value-flow matrix：**83 cases**，所有正负检查及边界检查通过。
- ground-truth `--view all`：**5788 scored / 5548 primary_hit / 240 primary_miss**，与基线一致。
- `classify_ground_truth_failures.py --release-check`：通过，240 个既有 mismatch 分类文件保持一致。
- Python 3.9 grammar 检查及 `git diff --check` 通过；没有增加运行时第三方依赖。
- 八个切片的完整 JSON、两组交错对照的 payload 指纹、六次完整 Flow snapshot 指纹一致。

验证摘要保存在 [verification.json](verification.json)。生产代码、相关测试与架构文档
已修改；完整项目的两个 180s timeout 保留为尚未解决的性能限制。
