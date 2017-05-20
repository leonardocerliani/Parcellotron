# -*- coding: utf-8 -*-

import nibabel as nib
import numpy as np
import scipy.stats as st
from scipy.optimize import curve_fit


def matrix_log2(matrix):
    """ Apply log in base 2 on the matrix
    Parameters
    ----------
    matrix = 2D np.array
        Typically a 2D matrix seed by target
    Returns
    -------
    matrix_log2 : 2D np.array
        log2 of connectivity_matrix + 1
    """

    matrix_log2 = np.log2(matrix + 1)

    return matrix_log2



def matrix_zscore(matrix):
    """ Apply Z-score transformation on the matrix
    Parameters
    ----------
    matrix = 2D np.array
        Typically a 2D matrix seed by target

    Returns
    -------
    z_matrix : 2D np.array
        Zscore of connectivity_matrix, replacing each value with its Z score
        across ROIs
    """

    # Sometimes there are voxels with empty connectivity, which could be due to
    # either some NaNs in preprocessing phases or to isolation of the voxel.
    # They are typically in the order of 1/10000.
    # To deal with this, we inject random values from a gaussian (u=0,std=1),
    # so that we also don't have annoying NaNs in the similarity matrix

    # # To test the procedure, try to introduce some zero columns std
    # connectivity_matrix[:,2396:2397] = np.zeros([nROIs,1])
    # connectivity_matrix[:,85:86] = np.zeros([nROIs,1])

    nROIs = matrix.shape[0]

    ind_zerostd = np.where(np.sum(matrix, axis=0) == 0)

    if np.squeeze(ind_zerostd).any():
        numba_voxels_zerostd = np.array(ind_zerostd).shape[1]
        print("I found " + str(numba_voxels_zerostd) + " voxels with zero std.")
        print("I will replace them with normally distributed random numbers")

        matrix[:, [i for i in ind_zerostd]] =\
            np.random.randn(nROIs, 1, numba_voxels_zerostd)


    z_matrix = st.zscore(matrix, axis=0)

    return z_matrix

def rotate_components(phi, gamma = 1.0, q = 50, tol = 1e-6):
    """ Performs rotation of the loadings/eigenvectors
    obtained by means of SVD of the covariance matrix
    of the connectivity profiles.
    https://en.wikipedia.org/wiki/Talk:Varimax_rotation

    Parameters
    ----------
    phi: 2D np.array

    gamma: float
        1.0 for varimax (default), 0.0 for quartimax
    q: int
        number of iterations (default=50)
    tol: float
        tolerance for convergence (default=1e-6)
    """
    p,k = phi.shape
    r = np.eye(k)
    d=0
    for i in np.arange(q):
        d_old = d
        Lambda = np.dot(phi, r)
        u,s,vh = np.linalg.svd(np.dot(phi.T,np.asarray(Lambda)**3 - (gamma/p) *\
                         np.dot(Lambda, np.diag(np.diag(np.dot(
                             Lambda.T,Lambda))))))
        r = np.dot(u, vh)
        d = np.sum(s)
        if d_old != 0 and d / d_old < 1 + tol: break
    return np.dot(phi, r)

def fit_power(eigvals_rot):
    """Performs power curve fitting on the rotated eigenvalues
    to obtain the estimated number of PCA components
    Parameters
    ----------
    eigvals_rot: vector
    Returns
    -------
    npc : int
        number of principal components
    """


    L = eigvals_rot

    # Consider only the first 50 eigenvalues, otherwise the
    # curve fitting could be excessively driven by the right
    # tail of the distribution, which has very low values.
    L = L[0:50]

    # Define the fitting function for L
    def powerfunc(x, amp, exponent):
        return amp * (x ** exponent)

    # Define a number of x points corresponding to len(L)
    xL = np.arange(len(L))+1

    # Perform curve fitting
    popt, _ = curve_fit(powerfunc, xL, L, method='lm')

    # Calculate the distance from the origin, which is interpreted
    # as the elbow point
    x = np.linspace(1, 50, 1000)
    y = powerfunc(x, *popt)

    d = np.sqrt(x**2 + y**2)
    i0 = np.where(d == np.min(d))

    x0 = x[np.squeeze(i0)]
    y0 = y[np.squeeze(i0)]

    # Establish the number of principal components on the basis of this
    npc = np.int(np.round(x0))
    return npc
