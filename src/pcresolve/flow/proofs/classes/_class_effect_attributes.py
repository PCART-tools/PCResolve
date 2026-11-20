## @package pcresolve.flow.proofs.classes._class_effect_attributes
#  Collect attributes written by bounded class effects.
#
#
#  Extracts written attribute names from supported class-effect records.
#  从受支持的类效果记录中提取被写入的属性名。



## Collect written attribute names from supported class-effect records.
## 从受支持的类效果记录中收集被写入的属性名。
#
#  @param records Class-effect records; each supplies its written attribute names.
#  @return Set of attribute names written by the records.
def written_attributes(records):
    return {name for record in records for name in record['attributes']}
