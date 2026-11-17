## @package pcresolve.flow.proofs.classes._class_effect_attributes
#  Collect attributes written by bounded class effects.
#
#
#  Extracts written attribute names from supported class-effect records.
#  从受支持的类效果记录中提取被写入的属性名。



def written_attributes(records):
    return {name for record in records for name in record['attributes']}
