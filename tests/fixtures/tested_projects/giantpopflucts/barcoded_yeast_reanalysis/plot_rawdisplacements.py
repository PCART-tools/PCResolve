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

df=pd.read_csv('frequencies.csv')

freqcutoff_lr=7e-4
freqcutoff_ur=2e-3
#freqcutoff_lr=5e-4
#freqcutoff_ur=5e-3

sns.set_palette('Set1')

varrob=lambda col: (np.median(np.abs(col - np.median(col)))/0.67449)**2

for batch in [1,3,4]:
  plt.figure()
  dps=[]
  df0=df[(df['Batch_{}_t_1'.format(batch)]>freqcutoff_lr) & (df['Batch_{}_t_1'.format(batch)]<freqcutoff_ur)]
  zeta=pd.read_csv('zeta_batch{}_{}_to_{}.csv'.format(batch,freqcutoff_lr,freqcutoff_ur))

  for rep in [1,2,3]:
    d1 = df0[['Batch_{}_t_1'.format(batch),'Batch_{}_t_2_Rep_{}'.format(batch,rep), 'Batch_{}_t_3_Rep_{}'.format(batch,rep), 'Batch_{}_t_4_Rep_{}'.format(batch,rep)]]
    logdiff=np.diff(np.array(np.log(d1)),axis=1)
    #o=np.array(np.log(d1))
    #print(np.array(np.log(d1))[:,1])
    #plt.plot([0,1,2],logdiff.T,alpha=0.3)
    #print(logdiff[:,0])
    cc=np.hstack((logdiff[:,0],logdiff[:,1],logdiff[:,2]))
    #cc=list(o[:,1]-o[:,0]) + list(o[:,2]-o[:,1]) + list(o[:,3]-o[:,2])
    print('vars:',batch,rep,varrob(logdiff[:,0]),varrob(logdiff[:,1]),varrob(logdiff[:,2]))
    ll=len(logdiff[:,0])
    ts=[1]*ll + [2]*ll + [3]*ll
    ids=list(range(ll))*3
    zeta0=zeta[zeta['rep']==rep]
    totalvar = (
        [np.sum(zeta0[(zeta0['time point']==1) | (zeta0['time point']==2)]['zeta'])]*ll +
        [np.sum(zeta0[(zeta0['time point']==2) | (zeta0['time point']==3)]['zeta'])]*ll +
        [np.sum(zeta0[(zeta0['time point']==3) | (zeta0['time point']==4)]['zeta'])]*ll
      )

    dps.append(pd.DataFrame({'t':ts,'logdiff':cc,'rep':[rep]*len(cc),'bc':ids,'totalvar':totalvar}))

  dp=pd.concat(dps)
  dp.to_csv('raw_displacement_batch{}.csv'.format(batch),index=False)
  a3=sns.stripplot(data=dp,x='t',y='logdiff',hue='rep',alpha=0.5,dodge=True)
  sns.boxplot(data=dp,x='t',y='logdiff',hue='rep',dodge=True,
      showmeans=True, meanline=True, meanprops={'color': 'k', 'ls': '-', 'lw': 2,'alpha':0.5}, medianprops={'visible': False}, whiskerprops={'visible': False}, zorder=10,showfliers=False,showbox=False,showcaps=False)
  #sns.boxplot(data=dp,x='t',y='logdiff',hue='rep',dodge=True,**{'labels':None})
  handles, labels = a3.get_legend_handles_labels()
  l=plt.legend(handles[3:], labels[3:],title='Replicate',frameon=False,loc=(1.05, 0)) #
  plt.ylabel(r'log $f_t-$ log $f_{t-1}$')
  plt.xlabel(r'Second Day, $t$')
  plt.title('Batch {}'.format(batch))
  sns.despine()
  plt.tight_layout()
  #plt.ylim((-1.7,0.9))
  plt.savefig('raw_displacement_batch{}.pdf'.format(batch),format='pdf')




