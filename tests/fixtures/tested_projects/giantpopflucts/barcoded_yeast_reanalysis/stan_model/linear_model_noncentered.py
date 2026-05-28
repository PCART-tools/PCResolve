import pandas as pd
import scipy as sp 
import numpy as np 
import matplotlib.pyplot as plt
import pystan
import sys


stancode = """

data {
  int<lower=0> T;           // # time points
  int<lower=0> N;           // # of different data point
  int<lower=0> nbc;           // # of different barcodes
  int bc[N];           // barcode identity
  vector[N] s;        // fitnesses
  int d[N];            // day for each data point
  vector[N] vm;         // variance from measurement error for each  point 
}
parameters {
  vector<lower=-100,upper=100>[T] alpha;       // day effect
  real<lower=1e-5,upper=1> alpha_var; // variance of day effects
  real<lower=1e-5,upper=1> delta; // variance from intrinsic decoupling flucts
  vector<lower=-100,upper=100>[nbc] s_mean; // mean fitness effect
}
model {
  alpha_var ~ pareto(1e-5, 1);
  delta ~ pareto(1e-5, 1);

  for (a in 1:T) {
    alpha[a] ~ normal(0, 1);
  }

  for (i in 1:N) {
      s[i] ~ normal(s_mean[bc[i]] + alpha[d[i]]*sqrt(alpha_var), sqrt(delta + vm[i]));
  }
}
"""

batch=4

df=pd.read_csv('../raw_displacement_batch{}.csv'.format(batch))

nbc=np.max(df['bc'])+1
data_dic ={
  'T':3,
  'N':len(df),
  'nbc':nbc,
  'bc':list(np.array(df['bc']+1)),
  's':list(df['logdiff']),
  'd':list(df['t']),
  'vm':list(df['totalvar']),
}


sm = pystan.StanModel(model_code=stancode)
fit = sm.sampling(data=data_dic, iter=1000, chains=4,control=dict(max_treedepth=20,adapt_delta=0.8))


for pp in ['alpha_var','delta']:
  pd.DataFrame(fit.extract([pp])[pp],columns=[pp]).to_csv('posterior_{}_batch{}.csv'.format(pp,batch),index=False)

pd.DataFrame(fit.extract(['alpha'])['alpha'],columns=list(range(1,4))).to_csv('posterior_alphas_{}.csv'.format(batch),index=False)
pd.DataFrame(fit.extract(['s_mean'])['s_mean'],columns=list(range(1,nbc+1))).to_csv('posterior_smean_{}.csv'.format(batch),index=False)


