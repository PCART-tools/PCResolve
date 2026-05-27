import numpy as np 
import matplotlib.pyplot as plt
import scipy as sp
import scipy.special
import seaborn as sns
import pandas as pd
from matplotlib.legend_handler import HandlerTuple
import matplotlib
sns.set(style="ticks",font_scale=1.5)



batch=4

alphas=pd.read_csv('posterior_alphas_{}.csv'.format(batch))
de=pd.read_csv('posterior_alpha_var_batch{}.csv'.format(batch))

for i in ['1','2','3']:
	print(np.mean(alphas[i]*np.sqrt(de['alpha_var'])))