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


sns.set_palette('Set1')


for batch in [1,3,4]:
  plt.figure()
  
  dp=pd.read_csv('../raw_displacement_batch{}.csv'.format(batch))
  a3=sns.swarmplot(data=dp,x='t',y='logdiff',hue='rep',alpha=0.5,dodge=True)
  sns.boxplot(data=dp,x='t',y='logdiff',hue='rep',dodge=True,
      showmeans=True, meanline=True, meanprops={'color': 'k', 'ls': '-', 'lw': 2,'alpha':0.5}, medianprops={'visible': False}, whiskerprops={'visible': False}, zorder=10,showfliers=False,showbox=False,showcaps=False)
  #sns.boxplot(data=dp,x='t',y='logdiff',hue='rep',dodge=True,**{'labels':None})
  handles, labels = a3.get_legend_handles_labels()
  l=plt.legend(handles[3:], labels[3:],title='Replicate',frameon=False,loc=(1.05, 0)) #
  
  alphas=pd.read_csv('posterior_alphas_{}.csv'.format(batch))
  de=pd.read_csv('posterior_alpha_var_batch{}.csv'.format(batch))
  means=[]
  lci=[]
  uci=[]
  for t in [1,2,3]:
    v=np.array(alphas[str(t)]*np.sqrt(de['alpha_var']))
    mm=np.mean(v)
    means.append(mm)
    lci.append(mm- np.quantile(v,0.025))
    uci.append(np.quantile(v,0.975) - mm)

  plt.errorbar([0,1,2],means,yerr=np.vstack((lci,uci)),fmt='ks',zorder=10,alpha=0.7)
  plt.ylabel(r'log $f_t-$ log $f_{t-1}$')
  plt.xlabel(r'Second Day, $t$')
  plt.title('Batch {}'.format(batch))
  sns.despine()
  plt.tight_layout()
  #plt.ylim((-1.7,0.9))
  plt.show()
  #plt.savefig('raw_displacement_batch{}.pdf'.format(batch),format='pdf')




