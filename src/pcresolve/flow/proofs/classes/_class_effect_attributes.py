## @package pcresolve.flow.proofs.classes._class_effect_attributes
#  Attributes written by bounded class effects.


## Collect possible class slots changed by already bounded creation phases.
## 收集已完成有界分析的创建阶段可能改变的类属性。
#
#  @param records Complete source creation-hook records for this class hierarchy.
#  @return Set of possible attribute spellings; presence and values remain unmodeled.
def written_attributes(records):
    return {name for record in records for name in record['attributes']}
