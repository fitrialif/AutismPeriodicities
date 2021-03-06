import numpy as np
import scipy.io as sio
from scipy import sparse
import time
from sklearn.decomposition import PCA
from SlidingWindowVideoTDA.FundamentalFreq import *
from SlidingWindowVideoTDA.TDA import *
from SlidingWindowVideoTDA.VideoTools import *

def getMeanShift(X, theta = np.pi/16):
    N = X.shape[0]
    eps = np.cos(theta)
    XS = X/np.sqrt(np.sum(X**2, 1))[:, None]
    D = XS.dot(XS.T)
    J, I = np.meshgrid(np.arange(N), np.arange(N))
    J = J[D >= eps]
    I = I[D >= eps]
    V = np.ones(I.size)
    D = sparse.coo_matrix((V, (I, J)), shape=(N, N)).tocsr()
    XMean = np.zeros(X.shape)
    for i in range(N):
        idx = D[i, :].nonzero()[1]
        XMean[i, :] = np.mean(X[idx, :], 0)
    return XMean

def getMeanShiftKNN(X, K):
    N = X.shape[0]
    D = np.sum(X**2, 1)[:, None]
    D = D + D.T - 2*X.dot(X.T)
    allidx = np.argsort(D, 1)
    XMean = np.zeros(X.shape)
    for i in range(N):
        idx = allidx[i, 0:K]
        XMean[i, :] = np.mean(X[idx, :], 0)
    return XMean

def getCSM(X, Y):
    """
    Return the Euclidean cross-similarity matrix between the M points
    in the Mxd matrix X and the N points in the Nxd matrix Y.
    :param X: An Mxd matrix holding the coordinates of M points
    :param Y: An Nxd matrix holding the coordinates of N points
    :return D: An MxN Euclidean cross-similarity matrix
    """
    C = np.sum(X**2, 1)[:, None] + np.sum(Y**2, 1)[None, :] - 2*X.dot(Y.T)
    C[C < 0] = 0
    return np.sqrt(C)

def getSlidingWindow(XP, dim, estimateFreq = False, derivWin = -1):
    """
    Return a sliding window video
    :param XP: An N x d matrix of N frames each with d pixels
    :param dim: The dimension of the sliding window
    :param estimateFreq: Whether or not to estimate the fundamental frequency
    or to just use dim as the window size with Tau = 1
    :param derivWin: Whether or not to do a time derivative of each pixel
    :returns: XS: The sliding window video
    """
    X = np.array(XP)
    #Do time derivative
    if derivWin > -1:
        X = getTimeDerivative(X, derivWin)[0]
    pca = PCA(n_components = 1)

    Tau = 1
    dT = 1
    #Do fundamental frequency estimation
    if estimateFreq:
        xpca = pca.fit_transform(X)
        (maxT, corr) = estimateFundamentalFreq(xpca.flatten(), False)
        #Choose sliding window parameters
        Tau = maxT/float(dim)

    #Get sliding window
    if X.shape[0] <= dim:
        return np.array([[0, 0]])
    XS = getSlidingWindowVideo(X, dim, Tau, dT)

    #Mean-center and normalize sliding window
    XS = XS - np.mean(XS, 1)[:, None]
    XS = XS/np.sqrt(np.sum(XS**2, 1))[:, None]
    return XS

def getPersistencesBlock(XP, dim, estimateFreq = False, derivWin = -1):
    """
    Return the Sw1Pers score of this block
    """
    XS = getSlidingWindow(XP, dim, estimateFreq, derivWin)
    #XS = getMeanShift(XS)
    D = getCSM(XS, XS)
    Pers = 0
    I = np.array([[0, 0]])
    try:
        PDs2 = doRipsFiltrationDM(D, 1, coeff=41)
        I = PDs2[1]
        if I.size > 0:
            Pers = np.max(I[:, 1] - I[:, 0])
    except Exception:
        print "EXCEPTION"
    return {'D':D, 'P':Pers, 'I':I}

def getD2ChiSqr(XP, dim, estimateFreq = False, derivWin = -1):
    """
    Return the Chi squared distance to the perfect circle distribution
    """
    XS = getSlidingWindow(XP, dim, estimateFreq, derivWin)
    ##TODO
