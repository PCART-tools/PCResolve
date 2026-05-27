import numpy as np 
import matplotlib.pyplot as plt
import scipy as sp
import scipy.special
import seaborn as sns
import pandas as pd
sns.set(style="ticks",font_scale=1.5)

grey = '#949aa1'
batches=[]
varl=[]
names=[]
for batch in [1,3,4]:
	day_var = list(pd.read_csv('posterior_alpha_var_batch{}.csv'.format(batch))['alpha_var'])
	delta_var = list(pd.read_csv('posterior_delta_batch{}.csv'.format(batch))['delta'])
	vari=delta_var+day_var
	varl+=vari
	names+=['Intrinsic\n'+r'($\delta_I$)']*len(delta_var) + ['Extrinsic\n'+r'($\delta_E$)']*len(day_var)
	batches+=[batch]*len(vari)


df=pd.DataFrame({'variance':varl,'name':names,'Batch':batches})
plt.figure(figsize=[4.7, 5])
g=sns.barplot(data=df,x='name',y='variance',hue='Batch',ci=None,estimator=lambda x: np.median(x),palette='colorblind')
x_coords = [p.get_x() + 0.5*p.get_width() for p in g.patches]
y_coords = [p.get_height() for p in g.patches]

print(x_coords,y_coords)

mms=[]
ll=[]
uu=[]
for i,group in df.groupby(by=['name','Batch']):
	mi=np.median(group['variance'])
	mms.append(mi)
	ll.append(mi-np.quantile(group['variance'],0.025))
	uu.append(np.quantile(group['variance'],0.975)-mi)
dfm=pd.DataFrame({'med':mms,'l':ll,'u':uu})

errors = pd.DataFrame({'x':x_coords,'med':y_coords}).merge(dfm,on='med',how='inner')
print(errors)
grey = '#949aa1'
red='#d91e3a'
blue='#2086e6'
lightgrey='#cbd1d6'
darkgrey='#40464d'
plt.errorbar(errors['x'], errors['med'], yerr=np.vstack((np.array(errors['l']),np.array(errors['u']))), fmt=' ',zorder=200,ecolor=grey)
plt.xlabel('')
plt.ylabel('Variance between replicates')
plt.yscale('log')
sns.despine()
plt.legend(loc='upper left',title='Batch',frameon=False)
plt.tight_layout()
plt.savefig('variance_components.pdf',format='pdf')
'''
plt.figure(figsize=[4.7, 5])
#sns.boxplot(data=df,x='name',y='variance')
g=sns.barplot(data=df,x='name',y='variance',ci=None,estimator=lambda x: np.median(x),palette='Blues_r')
x_coords = [p.get_x() + 0.5*p.get_width() for p in g.patches]
y_coords = [p.get_height() for p in g.patches]

#dfm=df.groupby(by='names').median().reset_index()
mms=[]
ll=[]
uu=[]
for i,group in df.groupby(by='name'):
	mi=np.median(group['variance'])
	mms.append(mi)
	ll.append(mi-np.quantile(group['variance'],0.025))
	uu.append(np.quantile(group['variance'],0.975)-mi)
dfm=pd.DataFrame({'med':mms,'l':ll,'u':uu})

errors = pd.DataFrame({'x':x_coords,'med':y_coords}).merge(dfm,on='med',how='inner')
grey = '#949aa1'
red='#d91e3a'
blue='#2086e6'
lightgrey='#cbd1d6'
darkgrey='#40464d'
plt.errorbar(errors['x'], errors['med'], yerr=np.vstack((np.array(errors['l']),np.array(errors['u']))), fmt=' ',zorder=200,ecolor=grey)
plt.xlabel('')
plt.ylabel('Variance between replicates')
plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
sns.despine()
plt.tight_layout()
plt.savefig('variance_components_{}.png'.format(batch),dpi=600)
'''