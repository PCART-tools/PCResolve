## @package pcresolve.flow.index.generation
#  Determine whether a previously built flow index may be reused.
#
#
#  Compares source-document identities, read policy and ordered import roots
#  before sharing generation-local index facts across analysis runs.
#  在跨分析运行复用索引事实前，比较源码文档身份、读取策略和有序导入根目录。



## Compare the complete source generation and ordered module naming roots.
## 比较完整的源码代际与有序的模块命名根目录。
#
#  @param previous Previously indexed snapshot, if any.
#  @param current Newly captured source snapshot.
#  @param previous_roots Roots used for the prior index.
#  @param current_roots Roots requested by the current analysis.
#  @return True only when every selected document is the same cached version.
def same_generation(previous, current,
                    previous_roots, current_roots):
    return (previous is not None and previous.files == current.files
            and previous.policy == current.policy
            and tuple(previous_roots) == tuple(current_roots)
            and all(previous.documents[path] is current.documents[path]
                    for path in previous.files))
