# get frequencies of barcodes from Venkataram et al. (2016) raw data
import pandas as pd
import scipy as sp 
import numpy as np 
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.optimize
import random
import scipy.stats
import itertools
import copy
import statistics
from scipy.stats import norm
from scipy.optimize import minimize

sns.set(style="ticks",font_scale=1.5) #whitegrid


df = pd.read_csv('TableS3.csv')
df_fitness = pd.read_csv('TableS2.csv')[['barcode','Averaged_Fitness', 'Averaged_Error']]
#df_mutations = pd.read_csv('cell9121mmc5.csv')
df_ploidy = pd.read_csv('TableS1.csv')

print()

#df_ID = df_mutations.iloc[:, 9:].idxmax(axis=1).sort_index()
#df_ID = df_ID[(df_ID != 0) & (df_ID != 1)]

#df_mutations['ID'] = df_ID

df_rtot = df.loc[:, df.columns != 'barcode'].sum(axis=0)
df_freq = df.iloc[: , :-13].copy().dropna() #drop "500pool"
columns = list(df.columns)
for col in columns[1:-13]:
    df_freq[col] = df_freq[col]/(df_rtot[col])

df_freq=df_freq.merge(df_fitness,on='barcode',how='inner')
df_freq=df_freq.merge(df_ploidy,on='barcode',how='inner')

df_freq.drop_duplicates(subset='barcode',inplace=True)

bonferroni_correction=scipy.stats.norm().ppf(1-0.05/len(df_freq))
print(bonferroni_correction)



adaptiveornot=[]
for i,row in df_freq.iterrows():
  if (row['Averaged_Fitness']>bonferroni_correction*row['Averaged_Error']) and (row['Averaged_Fitness']>0.01):
    adaptiveornot.append(1)
  else:
    adaptiveornot.append(0)


df_freq['Adaptive']=adaptiveornot

df_freq.to_csv('frequencies.csv',index=False)


