import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt

def normalize(v):
    avr = np.mean(v)
    std = np.std(v)
    return (v-avr)/std, avr, std

def recover(w, avr, std):
    return w*std+avr

def polynomialResidue(c, x, y):
    pol = np.poly1d(c[::-1])
    res = pol(x)-y
    return res.dot(res)

def polynomialJacobian(c, x, y):
    pol = np.poly1d(c[::-1])
    dif = 2.0*(pol(x)-y)
    der = np.zeros_like(c)
    xp  = np.ones_like(x)
    for i in range(len(c)):
        der[i] = dif.dot(xp)
        xp = xp*x
    return der

def regs(odrs, cons=()):
    s = []
    f = plt.figure()
    for idx in range(len(odrs)):
        odr = odrs[idx]
        c0  = np.zeros((odr+1,))
        c   = minimize(residue, c0, method='SLSQP',
                       jac=jacobian, constraints=cons)
        pol = np.poly1d(c.x[::-1])
        s.append(c.x)

        plt.subplot(2, 2, idx+1)
        plt.tight_layout()
        plt.plot(x0, y0, 'bo', fillstyle='none')
        plt.plot(x0, np.sin(x0), 'b--', linewidth=2)
        plt.plot(x0, recover(pol(x), yavr, ystd), 'r-', linewidth=2)
        plt.grid()
        plt.title('Order = {0:d}'.format(odr))
    return f, s

if __name__ == "__main__":
    # Generate sample dataset
    np.random.seed(10)
    x0 = np.arange(60, 300, 4) * np.pi/180.0
    y0 = np.sin(x0) + np.random.normal(0, 0.15, len(x0))
    x, xavr, xstd = normalize(x0)
    y, yavr, ystd = normalize(y0)

    f = plt.figure()
    plt.plot(x0, y0, 'bo', fillstyle='none')
    plt.grid()
    plt.xlabel('x')
    plt.ylabel('y')
    plt.show()

    # Define the objective function
    residue  = lambda c: polynomialResidue(c, x, y)
    jacobian = lambda c: polynomialJacobian(c, x, y)

    # The polynomial orders to consider
    odrs = [6, 9, 12, 15]
    
    # Simple regression
    f1, s1 = regs(odrs)
    
    # Lasso regression
    alph = 10.
    cons = ({'type' : 'ineq',
             'fun'  : lambda c: alph-np.sum(np.abs(c))},)
    f2, s2 = regs(odrs, cons)
    
    # # Ridge regression
    # beta = 1
    # cons = ({'type' : 'ineq',
    #          'fun'  : lambda c: beta*2-c.dot(c),
    #          'jac'  : lambda c: -2.0*c},)
    # f3, s3 = regs(odrs, cons)

    # Comparison of regression coefficients
    c = np.polyfit(x0, y0, 16)
    plt.figure()
    plt.semilogy(np.abs(s1[3]), 'bo', label='Simple')
    plt.semilogy(np.abs(s2[3]), 'rs', label='Lasso')
    # plt.semilogy(np.abs(s3[3]), 'gv', label='Ridge')
    plt.grid()
    plt.xlabel('Order')
    plt.ylabel('Coefficients')
    plt.legend()
    
    plt.show()
