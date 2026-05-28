# mean-variance scaling behaviors
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
sns.set(style="ticks",font_scale=1.8) #whitegrid

df00=pd.read_csv('frequencies.csv')
mat1 = np.array(df00[['Batch_3_t_2_Rep_1', 'Batch_3_t_2_Rep_2', 'Batch_3_t_2_Rep_3']])
mat2 = np.array(df00[['Batch_1_t_2_Rep_1', 'Batch_1_t_2_Rep_2', 'Batch_1_t_2_Rep_3']])

adapt=np.array(list(df00['Adaptive'])*2)

msa=np.mean(mat1,axis=1)
vsa=np.var(np.log(mat1),axis=1)
msb=np.mean(mat2,axis=1)
vsb=np.var(np.log(mat2),axis=1)

ms=np.concatenate((msa,msb))
vs=np.concatenate((vsa,vsb))

print(len(ms),len(adapt))

ms=ms[pd.notnull(vs)]
vs=vs[pd.notnull(vs)]


vs=vs[(ms<5e-3) & (ms>1e-6)]
ms=ms[(ms<5e-3) & (ms>1e-6)]


def boot_powerlaw(t,x,nboot=100):
  y=list(zip(list(t),list(x)))
  ps=[]
  for i in range(nboot):
    yi=random.choices(y,k=len(y))
    ti,xi=zip(*yi)
    p1=np.polyfit(np.log(ti),np.log(xi),1)[0]
    ps.append(p1)
  return np.std(ps)



ms1=ms[(ms<5e-5) & (ms>1e-6)]
vs1=vs[(ms<5e-5) & (ms>1e-6)]
p1=np.polyfit(np.log(ms1),np.log(vs1),1)[0]
print(p1,boot_powerlaw(ms1,vs1))

ms2=ms[ms>3e-4]
vs2=vs[ms>3e-4]
p2=np.polyfit(np.log(ms2),np.log(vs2),1)[0]
print(p2,boot_powerlaw(ms2,vs2))

print(p1,p2)

def convolve(t,x,tdiv,window=0.3):
  xs=[]
  for ti in tdiv:
    xs.append(np.mean(x[(t>=ti*(1-window)) & (t<=ti*(1+window))]))
  return np.array(xs)

def convolve_boot(t,x,tdiv,nboot=100):
  y=list(zip(list(t),list(x)))
  xis=[]
  for i in range(nboot):
    yi=random.choices(y,k=len(y))
    ti,xi=zip(*yi)
    #print(xi)
    xc=convolve(np.array(ti),np.array(xi),tdiv)
    xis.append(xc)
  xis=np.stack(xis)
  lci=np.quantile(xis,0.025,axis=0)
  uci=np.quantile(xis,0.975,axis=0)
  return lci,uci


tc=np.linspace(4e-6,3e-3,10**4)
xc=convolve(ms,vs,tc)
lci,uci=convolve_boot(ms,vs,tc)
#print(xc)


green='#59b332' # BCDCB7
purple='#9c34bf' # CCB9D3 

grey = '#949aa1'
red='#d91e3a'
blue='#2086e6'
lightgrey='#cbd1d6'
darkgrey='#40464d'


# get confidence intervals
# show x^2 and x
plt.figure()
#sns.kdeplot(x=ms,y=vs,fill=True)
plt.plot(ms,vs,'o',alpha=0.1,markersize=4,color=grey)
plt.plot(tc,xc,'k')
plt.fill_between(tc,lci,uci,color='k',alpha=0.4)


#plt.plot(ms[adapt==1],vs[adapt==1],'s',alpha=0.1,markersize=4,color=grey)
#plt.plot(ms[adapt==0],vs[adapt==0],'o',alpha=0.1,markersize=4,color=grey)

a1=np.mean(xc[(tc<0.6e-4)]/(tc[(tc<0.6e-4)]**-1))
a2=np.mean(xc[tc>3e-4]/(tc[tc>3e-4]**0))

plt.plot(tc[tc<3e-5],a1*tc[tc<3e-5]**-1,'--',color=blue,linewidth=3)
plt.plot(tc[tc>8e-4],a2*tc[tc>8e-4]**0,'--',color=red,linewidth=3)

plt.xlabel(r'$\langle f \rangle$')
plt.ylabel(r'var log $f$')

plt.yscale('log')
plt.xscale('log')
plt.ylim((8e-4,2e-1))
plt.xlim((7e-6,4.5e-3))
sns.despine()
plt.tight_layout()
plt.savefig('scaling_1_log.pdf',format='pdf',transparent=True)

