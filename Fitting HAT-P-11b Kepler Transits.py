import numpy as np
inf = np.inf

import batman
from scipy.optimize import minimize as optmin

# Values from Huber et al 2017 -- Discovered Eclipse of HAT-P-11 inside Kepler Data
h11Per       = 4.88782433
h11t0        = 2454957.812464 - 2454833.0
h11Inc       = 88.99
h11ApRs      = 14.64
h11RpRs      = 0.05856
h11Ecc       = 0.26493
h11Omega     = 360-162.149
h11u1        = 0.646
h11u2        = 0.048

def generate_fake_transit_data(period, tcenter, inc, aprs, rprs, ecc, omega, u1, u2, offset, slope, curvature, 
                       times, noiseLevel=None, ldtype='quadratic', transitType='primary'):
  
  cleanModel = batman_wrapper_lmfit(period, tcenter, inc, aprs, rprs, ecc, omega, u1, u2, offset, slope, curvature, 
                       times, ldtype='quadratic', transitType='primary')
  
  if noiseLevel is None:
    noiseLevel = 1e-4
   
  noisyData = np.random.normal(cleanModel, noiseLevel)
  dataError = np.random.normal(noiseLevel, 1e-2*noiseLevel)
  return noisyData, dataError

def batman_wrapper_mle(params, times, ldtype='quadratic', transitType='primary'):

    period, tcenter, inc, aprs, rprs, ecc, omega, u1, u2, slope0, slope, curvature = params
    
    if offset == 1.0 and slope == 0.0 and curvature == 0.0:
        out_of_transit = 1.0
    else:
        out_of_transit = offset + slope*(times - times.mean()) + curvature*(times - times.mean())**2.
    
    bm_params           = batman.TransitParams() # object to store transit parameters

    bm_params.per       = period  # orbital period
    bm_params.t0        = tcenter # time of inferior conjunction
    bm_params.inc       = inc     # inclunaition in degrees
    bm_params.a         = aprs    # semi-major axis (in units of stellar radii)
    bm_params.rp        = rprs    # planet radius (in units of stellar radii)
    bm_params.ecc       = ecc     # eccentricity
    bm_params.w         = omega   # longitude of periastron (in degrees)
    bm_params.limb_dark = ldtype              # limb darkening model # NEED TO FIX THIS
    bm_params.u         = [u1, u2]                  # limb darkening coefficients # NEED TO FIX THIS

    m_eclipse = batman.TransitModel(bm_params, times, transittype=transitType)    # initializes model

    return m_eclipse.light_curve(bm_params) * out_of_transit

def batman_wrapper_lmfit(period, tcenter, inc, aprs, rprs, ecc, omega, u1, u2, offset, slope, curvature, 
                       times, ldtype='quadratic', transitType='primary'):

    # period, tcenter, inc, aprs, rprs, ecc, omega, u1, u2, offset, slope, curvature = params
    
    if offset == 1.0 and slope == 0.0 and curvature == 0.0:
        out_of_transit = 1.0
    else:
        out_of_transit = offset + slope*(times - times.mean()) + curvature*(times - times.mean())**2.
    
    bm_params           = batman.TransitParams() # object to store transit parameters

    bm_params.per       = period  # orbital period
    bm_params.t0        = tcenter # time of inferior conjunction
    bm_params.inc       = inc     # inclunaition in degrees
    bm_params.a         = aprs    # semi-major axis (in units of stellar radii)
    bm_params.rp        = rprs    # planet radius (in units of stellar radii)
    bm_params.ecc       = ecc     # eccentricity
    bm_params.w         = omega   # longitude of periastron (in degrees)
    bm_params.limb_dark = ldtype              # limb darkening model # NEED TO FIX THIS
    bm_params.u         = [u1, u2]                  # limb darkening coefficients # NEED TO FIX THIS

    m_eclipse = batman.TransitModel(bm_params, times, transittype=transitType)    # initializes model

    return m_eclipse.light_curve(bm_params) * out_of_transit

def loglikehood(params, uni_prior, times, flux, fluxerr, regularization=None, lam=0.5):
    model = batman_wrapper_mle(params, times)
    chisq = ((flux - model)/fluxerr)**2.
    if regularization is None:
        return -0.5*chisq.sum()
    elif regularization == 'Ridge':
        return -0.5*chisq.sum() + lam*np.sqrt((params**2).sum())
    elif regularization == 'LASSO':
        return -0.5*chisq.sum() + lam*abs(params).sum()

def logPrior(params, uni_prior, times, flux, fluxerr):
    for kp, (lower, upper) in enumerate(uni_prior):
        if params[kp] < lower or params[kp] > upper:
            return -np.inf
        return 0.0

def logPosterior(params, uni_prior, times, flux, fluxerr):
    logPriorNow = logPrior(params, uni_prior, times, flux, fluxerr)
    logLikeLNow = loglikehood(params, uni_prior, times, flux, fluxerr)
    return logLikeLNow + logPriorNow

def neg_logprobability(params, uni_prior, times, flux, fluxerr):
    return -2*logPosterior(params, uni_prior, times, flux, fluxerr)

periodIn    = h11Per
tcenterIn   = h11t0
incIn       = h11Inc
aprsIn      = h11ApRs
rprsIn      = h11RpRs
eccIn       = h11Ecc
omegaIn     = h11Omega
u1In        = h11u1
u2In        = h11u2
offset      = 1.0
slope       = 0.0
curvature   = 0.0

# Initial Parameters
initParams = [periodIn, tcenterIn, incIn, aprsIn, rprsIn, eccIn, omegaIn, u1In, u2In, offset, slope, curvature]

# Frozen Prior
uniPrior = np.array([
            [periodIn,periodIn],
            [tcenterIn, tcenterIn],
            [incIn, incIn],
            [aprsIn, aprsIn],
            [rprsIn, rprsIn],
            [eccIn,eccIn],
            [omegaIn,omegaIn],
            [u1In,u1In],
            [u2In,u2In]
           ])

# Partial UnFrozen Prior
uniPrior = np.array([
            [periodIn,periodIn], # uniform volume for period (== 0)
            [tcenterIn-0.1, tcenterIn+0.1], # uniform volume for tcenter (== 0.2)
            [80., 90.], # uniform volume for inclination
            [10, 20], # uniform volume for ApRs
            [0.01, 0.1], # uniform volume for RpRs
            [eccIn,eccIn], # uniform volume for ecc
            [omegaIn,omegaIn], # uniform volume for omega
            [0.6,0.7], # uniform volume for u1
            [0.0,0.1], # uniform volume for u2
            [-inf,inf],
            [-inf,inf],
            [-inf,inf]
           ])

nPts = 1000
tSim = np.linspace(h11t0 - 0.2, h11t0 + 0.2, nPts)
data, derr = generate_fake_transit_data(h11Per, h11t0, h11Inc, h11ApRs, h11RpRs, h11Ecc, h11Omega, h11u1, h11u2, 
                                        offset, slope, curvature, tSim, noiseLevel=0.1, 
                                        ldtype='quadratic', transitType='primary')

res = optmin(neg_logprobability, initParams, args=(uniPrior, tSim, data, derr), bounds=uniPrior)

print(res.x - initParams)

## FIRST TRY at LMFIT

from lmfit import Parameters, Model
p = Parameters()

p.add('period'   , value = 4.88782433, vary=False)
p.add('tcenter'    , value = 2454957.812464 - 2454833.0, vary=True)
p.add('inc'   , value = 88.99, vary=True)
p.add('aprs'  , value = 14.64, vary=True)
p.add('rprs'  , value = 0.05856, vary=True)
p.add('ecc'   , value = 0.26493, vary=False)
p.add('omega' , value = 360-162.149, vary=False)
p.add('u1'    , value = 0.646, vary=True)
p.add('u2'    , value = 0.048, vary=True)
p.add('offset', value = 1.0, vary=True)
p.add('slope'    , value = 0.0, vary=True)
p.add('curvature', value = 0.0, vary=True)

lc = Model(batman_wrapper_lmfit, independent_vars=['times', 'ldtype', 'transitType'])

fitResult = lc.fit(data        = data,
                   params      = p,
                   times       = tSim,
                   weights     = derr**(-2),
                   ldtype      = 'quadratic',
                   transitType = 'primary',
                   method      = 'powell')

print(fitResult.best_values)

# from lmfit import minimize, Parameters, Model
#
# initialParams = Parameters()
#
# initialParams.add_many(
#     ('period' , kep3period, False),
#     ('tcenter' , kep3t0, True, kep3t0 - 0.1, kep3t0 + 0.1),
#     ('inc' , kep3inc, True, 80., 90.),
#     ('aprs' , kep3aoR, True, 10, 20),
#     ('rprs' , kep3RpRs, True, 0.01, 0.1),
#     ('ecc' , kep3ecc, False),
#     ('omega' , kep3omeg, False),
#     ('u1' , kep3u1, True, 0.6, 0.7),
#     ('u2' , kep3u2, True, 0.0, 0.1),
#     ('offset', 1.0, True),
#     ('slope', 0.0, True),
#     ('curvature', 0.0, True))
#
# initialParams
#
# lc = Model(batman_wrapper_lmfit,
#               independent_vars = ['times', 'ldtype', 'transitType'])
#
# fitResult = lc.fit(fluxSliceK,
#                    weights     = 1 / ferrSliceK**2.,
#                    params      = initialParams,
#                    method      = 'powell',
#                    times       = timeSliceKmod,
#                    ldtype      = 'quadratic',
#                    transitType = 'primary')
#
# plt.plot(timeSliceKmod, fluxSliceK,'.')
# plt.plot(timeSliceKmod, fitResult.best_fit)
#
# residuals = fluxSliceK - fitResult.best_fit
# chisq     = np.sum((residuals / ferrSliceK)**2.)
# print(chisq / residuals.size)