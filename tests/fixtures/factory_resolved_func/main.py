from pydantic import create_model
from pydantic import create_model as aliased_create_model
import pydantic


DynamicModel = create_model("DynamicModel")
DynamicModel(dynamic_field=10)

AliasedModel = aliased_create_model("AliasedModel")
AliasedModel(dynamic_field=20)

QualifiedModel = pydantic.create_model("QualifiedModel")
QualifiedModel(dynamic_field=30)
