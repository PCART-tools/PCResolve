import numpy as np
from scipy.optimize import minimize

def weight(x):
    return (3.0/x[0]+np.sqrt(3.0)/x[1])
def weight_der(x):
    der = np.zeros(2)
    der[0] = -3.0/x[0]**2.0
    der[1] = -np.sqrt(3.0)/x[1]**2.0
    return der

x0 = [0.05,0.05]
cons = ({'type': 'ineq',
          'fun' : lambda x: np.array([-18.0*x[0]-6.0*np.sqrt(3.0)*x[1]+3.0]),
          'jac' : lambda x: np.array([-18.0, -6.0*np.sqrt(3.0)])})
res = minimize(weight, x0, jac=weight_der,constraints=cons, method='SLSQP',
options={'disp': True},bounds = ((0.05,0.1546),(0.05,0.1395)))
print('+++++++++res',res.x)
