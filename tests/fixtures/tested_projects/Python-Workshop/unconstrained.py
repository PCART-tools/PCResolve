import numpy as np
from scipy.optimize import minimize
import matplotlib
import numpy as np
import matplotlib.cm as cm
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

# Rosenbrock function
def rosen(x):
    """The Rosenbrock function"""
    return (100.0*(x[1]-x[0]**2.0)**2.0 + (1-x[0])**2.0)

# Rosenbrock gradient
def rosen_der(x):

    der = np.zeros(2)

    der[0] = -400*x[0]*(x[1]-x[0]**2) - 2*(1-x[0])
    der[1] = 200*(x[1]-x[0]**2)
    return der

# initial pt for optimization
x0 = np.array([0.0,0.0])

# optimize!
res = minimize(rosen, x0, method='BFGS', jac=rosen_der,options={'disp': True})
print('+++++++++res',res.x)
post_process_flag = 1


# post process
if (post_process_flag==1):
    delta = 0.025
    x = np.arange(-3.0, 3.0, delta)
    y = np.arange(-3.0, 3.0, delta)
    X, Y = np.meshgrid(x, y)

    Z = np.array(np.zeros((len(y),len(x))))
    for i in xrange(len(x)):
        for j in xrange(len(y)):
            loc_x = x[i]
            loc_y = y[j]

            loc = np.array([loc_x,loc_y])

            Z[j,i] = rosen(loc)

    levels = np.arange(0, 1000, 50)
    CS = plt.contour(X, Y, Z,levels)
    plt.clabel(CS, inline=100, fontsize=10)
    plt.plot(res.x[0],res.x[1],"*",markersize=20)
    plt.show()
