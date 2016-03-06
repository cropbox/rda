from ..estimation.base import Estimator

import itertools
import datetime
import multiprocessing as mp
import numpy as np
import pandas as pd

###############
# Calibration #
###############

def _calibrate_func(x):
    model, args, kwargs = x
    return model.calibrate(*args, **kwargs)

def calibrate(model, years, splitter_name, **kwargs):
    years = model._years(years)
    splitter = getattr(model, splitter_name)
    validate_years_list = splitter(years)
    calibrate_years_list = [sorted(set(years) - set(validate_years)) for validate_years in validate_years_list]
    args_list = [(model, [calibrate_years, False], kwargs) for calibrate_years in calibrate_years_list]

    pool = mp.Pool()
    coeffs = pool.map(_calibrate_func, args_list)
    pool.close()
    pool.join()

    keys = [tuple(k) for k in calibrate_years_list]
    model._coeffs = dict(zip(keys, coeffs))

##############
# Estimation #
##############

def _estimate_func(x):
    model, year = x
    return model.estimate_multi(year)

def estimate(models, year):
    argss = [(m, year) for m in models]

    pool = mp.Pool(len(models))
    estms = pool.map(_estimate_func, argss)
    pool.close()
    pool.join()

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

def preset(output, slugname, model, years, **kwargs):
    def filename(var):
        return output.outfilename('coeffs', '{}_{}'.format(slugname, var), 'npy')

    def load(var, callback):
        fn = filename(var)
        print('{} preset.load: {}'.format(datetime.datetime.now(), fn))
        try:
            setattr(model, var, np.load(fn).tolist())
        except:
            callback()
            np.save(fn, getattr(model, var))

    def single_calibrate():
        model.calibrate(years)

    def multi_calibrate():
        calibrate(model, years, '_splitter_k_fold', **kwargs)

    #HACK needed for metric()
    #FIXME is it still needed?
    model._calibrate_years = model._years(years)

    load('_coeff', single_calibrate)

    #HACK no time for multi param calibration
    model._coeffs = {'': model._coeff}

    load('_coeffs', multi_calibrate)
