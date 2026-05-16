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
