import pandas as pd

df = pd.read_csv("data.csv")

# Issue 1: self-referencing reassignment breaks the chain
df = df.dropna()

# After reassignment, df.dropna() should still resolve to pandas, not df()
df.info()

# Issue 2: subscript expression in assignment should trace through
df_clean = df[df.x > 0].copy()

# df_clean.to_csv() should be pandas, not local
df_clean.to_csv("out.csv", index=False)

# Issue 3: self-reassignment via attribute chain should keep original source
df_col = df["col"]
df_col = df_col.str.split(",")

# df_col.str.split() should still resolve to pandas, not df_col or local
df_col.str.split(",")
