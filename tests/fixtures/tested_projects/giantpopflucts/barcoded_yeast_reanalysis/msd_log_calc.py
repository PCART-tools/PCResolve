# calculate MSDs
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

batch=4

trafo=lambda x: np.log(x)
inv_trafo = lambda x: np.exp(x)

freqcutoff_lr=7e-4
freqcutoff_ur=2e-3
freqcutoff_l=trafo(freqcutoff_lr)
freqcutoff_u=trafo(freqcutoff_ur)




# get empirical kappa
kappas_emp = {
  (1,2):{},
  (2,3):{},
  (3,4):{},
  (1,3):{},
  (2,4):{},
}

#remember that time 1 only has one measurement
for tp in kappas_emp:
  mu=[]
  logf_l=[]
  for ti in tp:
    if ti==1:
      logf=trafo(np.array(df00[['Batch_{}_t_{}'.format(1,ti)]]))
      mu.append(logf.flatten())
      logf_l.append(np.hstack([logf]*3))
    else:
      logf=trafo(np.array(df00[['Batch_{}_t_{}_Rep_1'.format(batch,ti), 'Batch_{}_t_{}_Rep_2'.format(batch,ti), 'Batch_{}_t_{}_Rep_3'.format(batch,ti)]]))
      mu.append(np.mean(logf,axis=1))
      logf_l.append(logf)
  s = np.hstack([np.vstack(mu[1]-mu[0])]*3)
  phi = logf_l[1] - logf_l[0]# - s
  kappa_mean=[]
  kappa_std=[]
  for i in [0,1,2]:
    col=phi[:,i]
    col = col[(mu[0]>freqcutoff_l) & (mu[0]<freqcutoff_u) & (pd.notnull(col))]
    vv = (np.median(np.abs(col - np.median(col)))/0.67449)**2
    kappa_mean.append(vv)
    
    coll=list(col)
    boot=[]
    for j in range(200):
      coi=random.choices(coll,k=len(coll))
      vi = (np.median(np.abs(coi - np.median(coi)))/0.67449)**2
      boot.append(vi)
    kappa_std.append(np.std(boot))
  kappas_emp[tp]['kappa']=kappa_mean
  kappas_emp[tp]['kappa std']=kappa_std

print(kappas_emp)

#map of flat indices to 
indexmap = {
  (1,1):0,
  (1,2):0,
  (1,3):0,
  (2,1):1,
  (2,2):2,
  (2,3):3,
  (3,1):4,
  (3,2):5,
  (3,3):6,
  (4,1):7,
  (4,2):8,
  (4,3):9,
}



def obj_single(kappa,kappa_std,ntransfers,beta1,beta2,delta):
  kappa_est = beta1 + beta2 + np.float(ntransfers)*delta
  return ((kappa_est - np.float(kappa))/np.float(kappa_std))**2

# add up objective functions across all kappas
def add_obj(theta):
  mse=0
  for (t1,t2) in kappas_emp:
    for rep in [1,2,3]:
      beta1=np.exp(theta[indexmap[t1,rep]])
      beta2=np.exp(theta[indexmap[t2,rep]])
      delta=np.exp(theta[-1])
      mse+=obj_single(kappas_emp[(t1,t2)]['kappa'][rep-1],kappas_emp[(t1,t2)]['kappa std'][rep-1],t2-t1,beta1,beta2,delta)
  #print(theta)
  #print('mse:',mse)
  return mse

bounds=[(np.log(1e-4),np.log(5e-2))]*11

res=sp.optimize.dual_annealing(lambda theta: add_obj(theta), bounds,local_search_options={"method": "L-BFGS-B"})
print(res)
####
dts=[1,2]
msd={
  1:[],
  2:[],
}

for tp in kappas_emp:
  for rep in [1,2,3]:
    kappa = np.array(kappas_emp[tp]['kappa'])

    ms=kappa - np.exp(res.x[indexmap[tp[0],rep]])  - np.exp(res.x[indexmap[tp[1],rep]])
    msd[tp[1]-tp[0]].append(ms)

msdl=[]
for t in dts:
  msdl.append(np.mean(msd[t]))
print('point estimate:',msdl)

# calculate errors
dts=[1,2]
e1=[]
e2=[]
for i in range(50):
  msd={
    1:[],
    2:[],
  }

  for tp in kappas_emp:
    for rep in [1,2]:
      kappa = np.array(kappas_emp[tp]['kappa'])
      kappa_std = np.array(kappas_emp[tp]['kappa std'])

      ms=np.random.normal(loc=kappa,scale=kappa_std) - np.exp(res.x[indexmap[tp[0],rep]])  - np.exp(res.x[indexmap[tp[1],rep]])
      msd[tp[1]-tp[0]].append(ms)

  e1.append(np.mean(msd[1]))
  e2.append(np.mean(msd[2]))

stds=[np.std(e1),np.std(e2)]
print('stds:',stds)


# save data
pd.DataFrame({'Batch':[batch]*2,'dt':dts,'msd':msdl,'msd stderr':stds}).to_csv('msd_batch{}_{}_to_{}.csv'.format(batch,freqcutoff_lr,freqcutoff_ur))
tps=[]
reps=[]
merr=[]
for (tp,rep) in indexmap:
  index=indexmap[(tp,rep)]
  merr.append(np.exp(res.x[index]))
  tps.append(tp)
  reps.append(rep)

pd.DataFrame({'time point':tps,'rep':reps,'zeta':merr}).to_csv('zeta_batch{}_{}_to_{}.csv'.format(batch,freqcutoff_lr,freqcutoff_ur))

'''
tl=[2,3,4]

plt.figure()
for batch in [1,3,4]:
  vl=[]
  for ti in tl:
    mat1 = np.array(df00[['Batch_{}_t_{}_Rep_1'.format(batch,ti), 'Batch_{}_t_{}_Rep_2'.format(batch,ti), 'Batch_{}_t_{}_Rep_3'.format(batch,ti)]])

    ms=np.mean(mat1,axis=1)
    vs=np.var(np.log(mat1),axis=1)


    ms=ms[pd.notnull(vs)]
    vs=vs[pd.notnull(vs)]


    vs=vs[(ms<8e-3) & (ms>3e-6)]
    ms=ms[(ms<8e-3) & (ms>3e-6)]


    def boot_powerlaw(t,x,nboot=100):
      y=list(zip(list(t),list(x)))
      ps=[]
      for i in range(nboot):
        yi=random.choices(y,k=len(y))
        ti,xi=zip(*yi)
        p1=np.polyfit(np.log(ti),np.log(xi),1)[0]
        ps.append(p1)
      return np.std(ps)



    #ms1=ms[(ms<2e-4) & (ms>1e-5)]
    #vs1=vs[(ms<2e-4) & (ms>1e-5)]

    ms2=ms[ms>2e-3]
    vs2=vs[ms>2e-3]

    print(ti,np.mean(vs2))
    vl.append(np.mean(vs2))
    #plt.plot([ti]*len(vs2),vs2,'.',alpha=0.3)

  plt.plot(tl,vl)
#plt.yscale('log')
plt.tight_layout()
plt.show()

'''
'''
# get confidence intervals
# show x^2 and x
# color by mutation type
plt.figure()
#sns.kdeplot(x=ms,y=vs,fill=True)
plt.plot(ms,vs,'o',alpha=0.1,markersize=4,color=grey)
plt.plot(tc,xc,'k')
plt.fill_between(tc,lci,uci,color='k',alpha=0.4)


#plt.plot(ms[adapt==1],vs[adapt==1],'s',alpha=0.1,markersize=4,color=grey)
#plt.plot(ms[adapt==0],vs[adapt==0],'o',alpha=0.1,markersize=4,color=grey)

a1=np.mean(xc[(tc<0.6e-4)]/(tc[(tc<0.6e-4)]**p1))
a2=np.mean(xc[tc>3e-4]/(tc[tc>3e-4]**p2))

plt.plot(tc[tc<1.5e-4],a1*tc[tc<1.5e-4]**p1,'--',color=blue,linewidth=2)
plt.plot(tc[tc>8e-4],a2*tc[tc>8e-4]**p2,'--',color=red,linewidth=2)

plt.xlabel(r'$\langle f \rangle$')
plt.ylabel(r'var log $f$')

plt.yscale('log')
plt.xscale('log')
plt.ylim((1e-4,1e-1))
plt.xlim((4e-5,4.5e-3))
sns.despine()
plt.tight_layout()
#plt.show()
plt.savefig('scaling_log.pdf',format='pdf',transparent=True)
'''

