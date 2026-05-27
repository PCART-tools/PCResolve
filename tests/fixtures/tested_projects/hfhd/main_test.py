from hfhd import sim
import numpy as np

if __name__ == "__main__":
    # generate a realization of prices
    factor_loadings = np.column_stack(
            (np.arange(10, 15)/10, np.flip(np.arange(10, 15)/10)))
    ind_loadings = np.zeros(factor_loadings.shape)
    u = sim.Universe(0.01,
                     [0.000000001, 0, 0.48, 0.5, 0.00000001],
                     [0.000000001, 0, 0.48, 0.5, 0.00000001],
                     [0.000000001, 0, 0.48, 0.5, 0.00000001],
                     factor_loadings,
                     ind_loadings,
                     0.5,
                     100,
                     'm')
    u.simulate(1)
    u.cond_cov()
