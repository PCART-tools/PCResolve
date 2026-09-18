import json


def decode(payload):
    return json.loads(payload)


data = decode('{}')
print(data)
