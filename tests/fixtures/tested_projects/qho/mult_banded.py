# -*- coding: utf-8  -*-

"""
    Multiplication ny a banded matrix using the same representation as
    scipy.linalg.solve_banded

    Copyright (C) 2014 Greg von Winckel

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

    Created: Sat Oct 19 00:11:30 MDT 2013

"""

import numpy as np
from scipy.linalg import solve_banded

def mult_banded(l_and_u,ab,x):

    n = len(x)

    pos = lambda j:j*(j>0)

    # Number of lower and upper diagonals
    l,u = l_and_u

    # Total number of bands     
    m = l+u+1

    # Number of zeros on the left
    zl = [pos(u-k) for k in range(m)]   
    
    # Number of zeros on the right
    zr = [pos(k-u) for k in range(m)]

    # Locations of nonzero elements in ab by row
    loc = [range(zl[k],n-zr[k]) for k in range(m)]

    def pad(k,v): return np.hstack((np.zeros(zr[k]),v,np.zeros(zl[k])))
    
    return sum([pad(k,ab[k,loc[k]]*x[loc[k]]) for k in range(m)])


if __name__ == '__main__':

    u = 2
    l = 4
    m = u+l+1
    n = 10

    ab = np.random.randn(m,n)
    x = np.random.randn(n)
    b = mult_banded((l,u),ab,x)
    y = solve_banded((l,u),ab,b)

    print(x-y)

