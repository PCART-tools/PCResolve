import pandas

df = pandas.DataFrame([{"x": 1, "y": 2}, {"x": 3, "y": 4}])
result = [v.x.mean() for k, v in df.groupby(["y"])]
