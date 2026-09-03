from helper import array_stream, list_stream


for array_value in array_stream():
    array_value.reshape(1, -1)

for list_value in list_stream():
    list_value.append(1)
