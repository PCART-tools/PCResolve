import numpy as np
import pandas as pd
from factory import pack, relay, strings, mixed, recursive, Producer, Value
from factory import default_pack, expanded, conflicting, generator_relay


for array in pack(np.array([1])):
    array.reshape(1)

for series in pack(pd.Series([1])):
    series.mean()

for local in pack(Value()):
    local.reshape(1)

for text in strings():
    text.strip()

for invalid in strings():
    invalid.append('x')

for relayed in relay(np.array([1])):
    relayed.reshape(1)

for method_value in Producer().pack(np.array([1])):
    method_value.reshape(1)

for ambiguous in mixed(np.array([1]), external_values):
    ambiguous.reshape(1)

for cyclic in recursive(np.array([1])):
    cyclic.reshape(1)

for rebound in pack(np.array([1])):
    rebound = Value()
    rebound.reshape(1)


def consume(values):
    for forwarded in values:
        forwarded.reshape(1)


consume(pack(np.array([1])))

for defaulted in default_pack():
    defaulted.strip()

for spread in expanded(external_values):
    spread.reshape(1)

for conflict in conflicting(np.array([1]), pd.Series([1]), flag):
    conflict.mean()

for generated in generator_relay(np.array([1])):
    generated.reshape(1)
