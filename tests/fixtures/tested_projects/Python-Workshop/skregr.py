import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn import linear_model

def regs(odrs, model):
    s = []
    f = plt.figure()
    for idx in range(len(odrs)):
        odr = odrs[idx]
        X   = np.column_stack([x**i for i in range(odr+1)])
        model.fit(X, y)
        s.append(model.coef_)
    
        plt.subplot(2, 2, idx+1)
        plt.tight_layout()
        plt.plot(x, y, 'bo', fillstyle='none')
        plt.plot(x, np.sin(x), 'b--', linewidth=2)
        plt.plot(x, model.predict(X), 'r-', linewidth=2)
        plt.grid()
        plt.title('Order = {0:d}'.format(odr))
    return f, s

if __name__ == "__main__":
    # Generate sample dataset
    np.random.seed(10)
    x = np.arange(60, 300, 4) * np.pi/180.0
    y = np.sin(x) + np.random.normal(0, 0.15, len(x))

    # The polynomial orders to consider
    odrs = [6, 9, 12, 15]

    # Various regression methods
    f1, s1 = regs(odrs, linear_model.LinearRegression(normalize=True))
    f2, s2 = regs(odrs, linear_model.Lasso(alpha=0.0001, normalize=True))
    f3, s3 = regs(odrs, linear_model.Ridge(alpha=0.0001, normalize=True))

    # Comparison of regression coefficients
    plt.figure()
    plt.semilogy(np.abs(s1[3]), 'bo', label='Simple')
    plt.semilogy(np.abs(s2[3]), 'rs', label='Lasso')
    plt.semilogy(np.abs(s3[3]), 'gv', label='Ridge')
    plt.grid()
    plt.xlabel('Order')
    plt.ylabel('Coefficients')
    plt.legend()
    
    plt.show()
