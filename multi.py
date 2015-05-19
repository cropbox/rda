from estimation import Estimator

import itertools
import multiprocessing as mp
import numpy as np
import pandas as pd

###############
# Calibration #
###############

def _calibrate_func(x):
    model, args, kwargs = x
    return model.calibrate(*args, **kwargs)

def calibrate(model, years, n=2, **kwargs):
    pool = mp.Pool()
    years = model._years(years)
    #yearss = itertools.combinations(years, n)
    yearss = sum([[list(x) for x in list(itertools.combinations(years, len(years)-i))] for i in range(n)], [])
    argss = [(model, [years, False], kwargs) for years in yearss]
    coeffs = pool.map(_calibrate_func, argss)
    model._coeffs = coeffs

##############
# Estimation #
##############

def _estimate_func(x):
    model, year = x
    return model.estimate_multi(year)

def estimate(models, year):
    pool = mp.Pool(len(models))
    argss = [(m, year) for m in models]
    estms = pool.map(_estimate_func, argss)
    names = [m.name for m in models]
    df = pd.concat(estms, keys=names, axis=1).fillna(0)
    #df['sum'] = df.sum(axis=1)
    dfsum = df.sum(axis=1)
    dfprod = (df + 1).prod(axis=1)
    df['sum'] = dfsum
    df['prod'] = dfprod
    return df

#########
# Caahe #
#########

def preset(slugname, model, years, n=3, **kwargs):
    def filename(var):
        return 'coeffs/current/{}_{}.npy'.format(slugname, var)

    def load(var, callback):
        fn = filename(var)
        try:
            setattr(model, var, np.load(fn).tolist())
        except:
            callback()
            np.save(fn, getattr(model, var))

    def single_calibrate():
        model.calibrate(years)

    def multi_calibrate():
        calibrate(model, years, n, **kwargs)

    load('_coeff', single_calibrate)

    #HACK no time for multi param calibration
    model._coeffs = [model._coeff]

    #load('_coeffs', multi_calibrate)
