from pydantic import create_model
from pydantic import parse_obj_as


if unknown_condition:
    factory = create_model
else:
    factory = parse_obj_as

DynamicModel = factory("DynamicModel")
DynamicModel(dynamic_field=10)
