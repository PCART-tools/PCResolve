from __future__ import division
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.linalg import solve_banded
from scipy.optimize import fmin_bfgs
from mult_banded import mult_banded


class QHO(object):
    """
    Quantum Harmonic Oscillator class 
    """
    def __init__(self,modes,N,T,i,f,g):
        """ 
        Create and store the three banded matrices for the system 
        (I,H, and X) since they will be reused
        """
        self.modes = modes
        self.N = N
        self.dt = T/N
        self.i = i
        self.f = f
        self.g = g

        self.u = np.zeros(N)

        j = np.arange(modes)

        # Identity matrix in banded form
        self.I = np.zeros((3,modes))
        self.I[1,:] = 1

        # Stationary part of Hamiltonian in banded form
        self.H = np.zeros((3,modes))
        self.H[1,:] = j+0.5

        # Dipole term in banded form
        self.X = np.zeros((3,modes))
        x = np.sqrt(j+1)/2   
        self.X[0,1:] = x[:-1]
        self.X[2,:-1] = x[:-1]

        # Allocate space for the state variable
        self.Y = np.zeros((modes,N+1),dtype=complex)

        # Allocate space for the adjoint variable  
        self.Z = np.zeros((modes,N+1),dtype=complex)

     
    def _solve_state(self,u):
        """
        Compute the solution to the state equation for a given 
        initial condition y[i]=1 and control u. See eq. (25)
        """

        self.Y[self.i,0] = 1

        for k in range(self.N):
            ab = self.I+0.5j*self.dt*(self.H+u[k]*self.X)
            b = mult_banded((1,1),np.conj(ab),self.Y[:,k])
            self.Y[:,k+1] = solve_banded((1,1),ab,b,overwrite_ab=True,
                                         overwrite_b=True,debug=False,
                                         check_finite=True)
        self.u = u

    def _solve_adjoint(self,u):
        """
        Compute the solution to the adjoint equation for a given 
        final condition and control u. See eq. (26)
        """
    
        self.Z[self.f,-1] = 1j*np.conj(self.Y[self.f,-1])

        for j in range(self.N):
            k = self.N-j-1
            ab = self.I+0.5j*self.dt*(self.H+u[k]*self.X)
            b = mult_banded((1,1),np.conj(ab),self.Z[:,k+1])
            self.Z[:,k] = solve_banded((1,1),ab,b,overwrite_ab=True,
                                       overwrite_b=True,debug=False,
                                       check_finite=True)
        self.u = u

        
    def cost(self,u):
        """ 
        Evaluate the reduced cost functional
        """         

        if not np.array_equal(u,self.u):
            self._solve_state(u)

        J = 0.5*self.dt*self.g*sum(u**2)-abs(self.Y[self.f,-1])**2
        return J

    def grad(self,u):
        """ 
        Evaluate the reduced gradient
        """         

        if not np.array_equal(u,self.u):
            self._solve_state(u)

        self._solve_adjoint(u)
        
        dex = range(1,self.N+1)


        # Inner product term in eq (28)
        ip = [np.dot((self.Z[:,j]+self.Z[:,j-1]),
              mult_banded((1,1),self.X,(self.Y[:,j]+self.Y[:,j-1]))) 
              for j in dex] 

        dJ = self.dt*(self.g*u+0.5*np.real(np.array(ip)))

        return dJ  

        
if __name__ == '__main__':

    # Number of Hermite functions
    modes = 10

    # Number of time steps
    N = 10

    # Control duration
    T = 10

    # Regularization parameter
    g = 1e-2
 
    # Time grid  
    t = np.linspace(0,T,N+1)  
 
    # Midpoints of time steps
    tm = 0.5*(t[:-1]+t[1:])

    # Initial guess of control
    u = 0.01*np.ones(N)

    # Instantiate Quantum Harmonic Oscillator for 0 -> 1 transition
    qho = QHO(modes,N,T,0,1,g)

    uopt = fmin_bfgs(qho.cost,u,qho.grad,args=(),gtol=1e-6,norm=np.inf, 
                     epsilon=1e-7, maxiter=1000, full_output=0, disp=1, 
                     retall=0, callback=None)


    for k in range(4):  

        t_old = t
        tm_old = tm

        u = np.repeat(uopt,2*np.ones(N,dtype=int))

        N *= 2
        t = np.linspace(0,T,N+1) 
        tm = 0.5*(t[:-1]+t[1:])

        g /= 2

        # Instantiate the controlled oscillator object
        qho = QHO(modes,N,T,0,1,g)

        # Compute a local minimizer 
        uopt = fmin_bfgs(qho.cost,u,qho.grad,args=(),gtol=1e-6,norm=np.inf, 
                         epsilon=1e-7, maxiter=1000, full_output=0, disp=1, 
                         retall=0, callback=None)



          

    fig = plt.figure(1,(16,7))
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
 
    ax1.set_xlabel('time',fontsize=16)
    ax1.set_title('Control',fontsize=18)
    ax1.tick_params(axis='both',which='major',labelsize=16) 

    ax2.set_xlabel('time',fontsize=16)
    ax2.set_title('State',fontsize=18)
    ax2.tick_params(axis='both',which='major',labelsize=16) 


    ax1.plot(tm,uopt) 
    ax2.plot(t,np.abs(qho.Y.T)**2)  

    plt.show() 



























