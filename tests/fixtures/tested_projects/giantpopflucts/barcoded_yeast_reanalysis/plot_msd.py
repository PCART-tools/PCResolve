# plot MSDs
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

dfs=[]
l=5e-4
u=5e-3
for batch in [1,3,4]:
  dfs.append(pd.read_csv('msd_batch{}_{}_to_{}.csv'.format(batch,l,u)))
df=pd.concat(dfs)

colors=sns.color_palette('colorblind')
plt.figure(figsize=[5, 4.8])
i=0
for (b,group) in df.groupby(by=['Batch']):
  msd=np.array(group['msd'])
  plt.errorbar(group['dt']+i/70,group['msd'],fmt='o-',yerr=2*group['msd stderr'],color=colors[i],alpha=0.8,label=b)
  plt.plot([0,1+i/70],[0,msd[0]],'--',color=colors[i],alpha=0.8)
  i+=1
plt.legend(title='Batch',frameon=False)
plt.ylabel('MSD Estimate')
plt.xlabel(r'Time difference, $\Delta t$')
plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
plt.yticks([0,0.5e-2,1e-2,1.5e-2])
plt.xticks([0,1,2])
plt.tight_layout()
sns.despine()
plt.savefig('msd_plot_{}_{}.pdf'.format(l,u),format='pdf')