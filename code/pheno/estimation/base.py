from ..data.dataset import DataSet
from ..data import path

import numpy as np
import scipy.optimize
import pandas as pd
import multiprocessing as mp
import datetime
import itertools
import collections
import copy
import random
import string

VALID_CHARS = frozenset("-_.() %s%s" % (string.ascii_letters, string.digits))
def _slugify(v):
    return ''.join(c for c in str(v) if c in VALID_CHARS)

def slugname(*args):
    return '_'.join([_slugify(k) for k in args])

MASK_DATETIME = None
MASK_JULIAN = 0
RESIDUAL_OBSERVATION_ERROR = -365.
RESIDUAL_ESTIMATION_ERROR = 365.

class ObservationError(Exception):
    pass

class EstimationError(Exception):
    pass

class Estimator(object):
    def __init__(self, dataset, coeff=None):
        self._dataset = dataset
        self._mets = dataset.weather()
        self._obss = dataset.observation()
        self._sds = dataset.start_dates()
        self._edo = 150 # 150 days after new year (around end of May)
        self._calibrate_years = None
        if coeff is None:
            coeff = {}
        self._coeff = coeff
        self._coeffs = {'': coeff}
        self.setup()

    def setup(self):
        pass

    @property
    def name(self):
        return str(self.__class__.__name__)

    @property
    def coeff_names(self):
        return []

    @property
    def actual_coeff_names(self):
        n = self.coeff_names
        # Ds (start date) coeff is not needed if start dates are predefined
        if self._sds is not None and 'Ds' in n:
            n.remove('Ds')
        return n

    @property
    def coeff(self):
        c = sorted(self._coeff.items(), key=lambda k: self.coeff_names.index(k[0]))
        return collections.OrderedDict(c)

    @property
    def default_options(self):
        return {
            'coeff0': {},
            'bounds': (),
            'grid': (),
            'fixed_coeff': {}
        }

    def options(self, **kwargs):
        opts = self.default_options.copy()
        opts.update(kwargs)
        return opts

    def copy(self):
        return copy.copy(self)

    # date range
    def start_date(self, year, coeff):
        if self._sds is not None:
            return self._sds.loc[year].date()
        try:
            # use Ds as an offset (e.g. Ds = 0 indicates the first day of the year)
            offset = int(coeff['Ds'])
            return datetime.date(year, 1, 1) + datetime.timedelta(days=offset)
        except:
            return datetime.date(year-1, 10, 1)

    def end_date(self, year, coeff):
        return datetime.date(year, 1, 1) + datetime.timedelta(days=self._edo)

    def _clip(self, year, coeff, skip_range_check=False):
        t0 = datetime.datetime.combine(self.start_date(year, coeff), datetime.time(0))
        t1 = datetime.datetime.combine(self.end_date(year, coeff), datetime.time(23))
        tz = self._mets.index.tz
        if tz is not None:
            t0 = tz.localize(t0)
            t1 = tz.localize(t1)
        df = self._mets[t0:t1]
        if not skip_range_check:
            assert df.index[0] == t0, "start date '{}' != '{}'".format(df.index[0], t0)
            assert df.index[-1] == t1, "end date '{}' != '{}'".format(df.index[-1], t1)
        return df

    def _years(self, years, skip_observation_check=False):
        mety = self._mets.dropna().reset_index().timestamp.dt.year.unique()
        if skip_observation_check:
            defy = mety
        else:
            obsy = self._obss.dropna().reset_index().year.unique()
            defy = np.intersect1d(mety, obsy, assume_unique=True)

        def parse(y, allow_default=False):
            if allow_default and y is None:
                return defy.tolist()
            elif isinstance(y, tuple) and len(y) == 2:
                # support (start, end) tuple for convenience
                start, end = y
                return np.intersect1d(defy, range(start, end+1)).tolist()
            elif hasattr(y, '__iter__') and not type(y) is str:
                return sorted(set(sum([parse(i) for i in y], [])))
            else:
                try:
                    iy = int(y)
                except:
                    raise ValueError("unrecognized format: y={}, years={}".format(y, years))
                return [iy] if iy in defy else []
        return parse(years, allow_default=True)

    # coefficient
    def _listify(self, coeff, keys=None):
        if keys is None:
            keys = self.actual_coeff_names
        if type(coeff) is list:
            return list(coeff)
        else:
            return list(coeff[k] for k in keys)

    def _dictify(self, values, keys=None, update={}):
        if keys is None:
            keys = self.actual_coeff_names
        if type(values) is dict:
            d = dict(values)
        else:
            d = dict(zip(keys, values))
        d.update(update)
        return d

    def _normalize(self, coeff):
        if type(coeff) is dict:
            return coeff
        else:
            return self._dictify(coeff)

    # date conversion
    def _julian(self, t, year):
        #return int(t.strftime('%j'))
        return (t.year - year)*365 + float(t.strftime('%j')) + t.hour/24. + t.minute/(24*60.) + t.second/(24*60*60.)

    def _mask(self, julian=False):
        return MASK_JULIAN if julian else MASK_DATETIME

    # estimation
    def _match(self, ts, value, descending=False):
        ts = ts.dropna()
        if descending:
            ts = -ts
            value = -value
        i = ts.searchsorted(value)[0]
        try:
            return ts.index[i]
        except:
            raise EstimationError("requirement '{}' cannot be matched".format(value))

    def _estimate(self, year, met, coeff):
        #return self._match(met.ix[:, -1], 1.0)
        raise NotImplementedError

    def estimate(self, year, coeff=None, julian=False, skip_range_check=False):
        if coeff is None:
            coeff = self._coeff
        else:
            coeff = self._normalize(coeff)
        try:
            met = self._clip(year, coeff, skip_range_check)
        except:
            #HACK: allow masking for exceptions on missing data
            raise ObservationError("weather cannot be clipped for '{}'".format(year))
        t = self._estimate(year, met, coeff).to_pydatetime()
        if julian:
            return self._julian(t, year)
        else:
            return t

    def estimate_safely(self, year, coeff=None, julian=False, skip_range_check=False):
        try:
            return self.estimate(year, coeff, julian, skip_range_check)
        except:
            return self._mask(julian)

    def estimates(self, years, coeff=None, julian=False, skip_observation_check=True, skip_range_check=False):
        s = [self.estimate_safely(y, coeff, julian, skip_range_check) for y in self._years(years, skip_observation_check)]
        return np.ma.masked_values(s, self._mask(julian))

    def estimate_multi(self, year, coeffs=None, julian=False):
        if coeffs is None:
            coeffs = self._coeffs
        if type(coeffs) is dict:
            coeffs = [self._normalize(c) for c in coeffs.values()]
        else:
            coeffs = [self._normalize(c) for c in coeffs]
        s = [self.estimate_safely(year, c, julian) for c in coeffs]
        ests = np.ma.masked_values(s, self._mask(julian))
        return pd.Series(ests).dropna()

    # observation
    def observe(self, year, julian=False):
        try:
            t = self._obss.loc[year].to_pydatetime().replace(hour=12)
        except:
            raise ObservationError("observation is not available for '{}'".format(year))
        if julian:
            return self._julian(t, year)
        else:
            return t

    def observe_safely(self, year, julian=False):
        try:
            return self.observe(year, julian)
        except:
            return self._mask(julian)

    def observes(self, years, julian=False, skip_observation_check=False):
        s = [self.observe_safely(y, julian) for y in self._years(years, skip_observation_check)]
        return np.ma.masked_values(s, self._mask(julian))

    # calibration
    def _calibrate(self, years, disp=True, seed=1, **kwargs):
        opts = self.options(**kwargs)

        try:
            fixed_coeff = opts['fixed_coeff']
        except:
            fixed_coeff = {}
        coeff0 = self._dictify(opts['coeff0'])
        coeff_names = self.actual_coeff_names.copy()
        fixed_coeff_index = []
        for k in fixed_coeff:
            coeff0.pop(k)
            coeff_names.remove(k)
            fixed_coeff_index.append(self.coeff_names.index(k))

        #HACK: remove Ds coeff if not used
        for k in self.coeff_names:
            if not k in coeff_names:
                fixed_coeff_index.append(self.coeff_names.index(k))

        x0 = self._listify(coeff0, coeff_names)
        args = (coeff_names, fixed_coeff)
        bounds = np.delete(opts['bounds'], fixed_coeff_index, axis=0)
        ranges = np.delete(opts['grid'], fixed_coeff_index, axis=0)

        def cost(x, *args):
            try:
                coeff_names, fixed_coeff = args
                coeff = self._dictify(x, coeff_names)
                coeff.update(fixed_coeff)
            except:
                coeff = x
            return self.metric(years, 'rmse', coeff)

        # new default to 'differential evolution'
        if 'method' not in opts:
            opts['method'] = 'evolution'

        if 'nelder-mead'.startswith(opts['method']):
            res = scipy.optimize.minimize(
                fun=cost,
                x0=x0,
                args=args,
                method='Nelder-Mead',
                options={
                    'disp': disp,
                },
            ).x
        elif 'basinhopping'.startswith(opts['method']):
            np.random.seed(seed)
            res = scipy.optimize.basinhopping(
                func=cost,
                x0=x0,
                niter=100,
                minimizer_kwargs={
                    'method': 'L-BFGS-B',
                    'bounds': bounds,
                    #'method': 'Nelder-Mead',
                    'args': args,
                },
                disp=disp,
            ).x
        elif 'evolution'.startswith(opts['method']):
            res = scipy.optimize.differential_evolution(
                func=cost,
                bounds=bounds,
                args=args,
                seed=seed,
                disp=disp,
            ).x
        elif 'brute'.startswith(opts['method']):
            res = scipy.optimize.brute(
                func=cost,
                ranges=ranges,
                args=args,
                full_output=True,
                finish=scipy.optimize.fmin,
                disp=disp,
            )[0]
        else:
            raise NameError("method '{}' is not defined".format(opts['method']))
        coeff = self._dictify(res, coeff_names, fixed_coeff)
        return coeff

    def calibrate(self, years=None, disp=True, save=True, **kwargs):
        years = self._years(years)
        coeff = self._calibrate(years, disp, **kwargs)
        if save:
            self._calibrate_years = years
            self._coeff = coeff
            self._coeffs[''] = coeff
        return coeff

    def calibrate_multi(self, years, splitter_name, save=True):
        years = self._years(years)
        splitter = getattr(self, splitter_name)
        validate_years_list = splitter(years)
        calibrate_years_list = [sorted(set(years) - set(validate_years)) for validate_years in validate_years_list]
        args_list = [([calibrate_years, False, False]) for calibrate_years in calibrate_years_list]

        with mp.Pool() as p:
            coeff_list = p.starmap(self.calibrate, args_list)
        keys = [tuple(k) for k in calibrate_years_list]
        coeffs = dict(zip(keys, coeff_list))
        if save:
            self._coeffs = coeffs
        return coeffs

    # preset from multi.py
    def preset(self, years, single=True, multi=True, output=None):
        if output is None:
            output = path.output

        key = slugname(
            self.name,
            self._dataset.met_station,
            self._dataset.obs_station,
            self._dataset.name,
            self._dataset.cultivar,
            self._dataset.stage,
            years,
        )

        def filename(var):
            return output.outfilename('coeffs', '{}_{}'.format(key, var), 'npy')

        def load(var, callback):
            fn = filename(var)
            print('{} - {} - preset.load: {}'.format(datetime.datetime.now(), self.name, fn))
            try:
                setattr(self, var, np.load(fn).tolist())
            except:
                value = callback()
                setattr(self, var, value)
                np.save(fn, value)

        #HACK needed for metric()
        #FIXME is it still needed?
        self._calibrate_years = self._years(years)

        if single:
            load('_coeff', lambda: self.calibrate(years))
        if multi:
            load('_coeffs', lambda: self.calibrate_multi(years, '_splitter_k_fold'))

    # validation
    def residual(self, year, coeff=None, func=None):
        try:
            obs = self.observe(year, julian=True)
            est = self.estimate(year, coeff, julian=True)
            if func is None:
                func = lambda o, e: e - o
            return func(obs, est)
        except ObservationError:
            return RESIDUAL_OBSERVATION_ERROR
        except EstimationError:
            return RESIDUAL_ESTIMATION_ERROR
            #return np.inf

    def residuals(self, years, coeff=None, ignore_estimation_error=False, func=None):
        #e = np.array([self.residual(y, coeff) for y in years])
        e = np.ma.masked_values([self.residual(y, coeff, func) for y in years], RESIDUAL_OBSERVATION_ERROR)
        if ignore_estimation_error:
            e = np.ma.masked_where(e == RESIDUAL_ESTIMATION_ERROR, e)
        return e

    @staticmethod
    def _is_higher_better(how):
        return how in {'ef', 'ef1', 'd', 'd1', 'dr', 'm', 'r'}

    def metric(self, years, how='e', coeff=None, ignore_estimation_error=False):
        years = self._years(years)

        how = how.lower()
        if how == 'observe':
            return self.residuals(years, coeff, ignore_estimation_error, func=lambda o, e: o)
        elif how == 'estimate':
            return self.residuals(years, coeff, ignore_estimation_error, func=lambda o, e: e)

        e = self.residuals(years, coeff, ignore_estimation_error)

        if how == 'e':
            return e
        elif how == 'rmse':
            return np.sqrt(np.mean(e**2))
        elif how == 'me':
            return np.mean(e)
        elif how == 'mae':
            return np.mean(np.abs(e))
        elif how == 'xe':
            try:
                return np.nanmax(np.abs(e))
            except:
                return np.nan

        o = self.observes(years, julian=True)
        p = self.estimates(years, coeff, julian=True)
        # use calibrate_years, not input years
        #TODO how to replace self._calibrate_years with ModelSuite.calibrate_years?
        #o_hat = self.observes(self._calibrate_years, julian=True).mean()
        o_hat = o.mean()
        d_est = p - o_hat
        d_obs = o - o_hat

        if how == 'ef':
            # Nash-Sutcliffe's coefficient of efficiency (Nash et al., 1970)
            return 1. - np.sum(e**2) / np.sum(d_obs**2)
        elif how == 'ef1':
            # Legates-McCabe's index (Legates et al., 1999)
            return 1. - np.sum(np.abs(e)) / np.sum(np.abs(d_obs))
        elif how == 'd':
            # Willmott's index of agreement (Willmott et al., 1980)
            return 1. - np.sum(e**2) / np.sum((np.abs(d_est) + np.abs(d_obs))**2)
        elif how == 'd1':
            # Willmott's another index of agreement (Willmott et al., 1985)
            return 1. - np.sum(np.abs(e)) / np.sum(np.abs(d_est) + np.abs(d_obs))
        elif how == 'dr':
            # Willmott's refined index of agreement (Willmott et al., 2012)
            c = 2
            dru = np.sum(np.abs(e))
            drl = c * np.sum(np.abs(d_obs))
            if dru <= drl:
                return 1. - dru / drl
            else:
                return drl / dru - 1.
        elif how == 'm':
            # Watterson's M (Watterson et al., 1996)
            mse = np.mean(e**2)
            p_hat = p.mean()
            return 2. / np.pi * np.arcsin(1. - mse / (p.var() + o.var() + (p_hat - o_hat)**2))
        elif how == 'r':
            # Mielke-Berry's R (Mielke et al., 2001)
            mae = np.mean(np.abs(e))
            n = len(years)
            pp = np.repeat(p, n)
            oo = np.tile(o, n)
            return 1. - mae / ((np.sum(np.abs(pp - oo))) / n**2)

    def _splitter_leave_n_out(self, years, n=1):
        return [list(y) for y in itertools.combinations(years, n)]

    def _splitter_k_fold(self, years, k=5, seed=1):
        random.seed(seed)
        random.shuffle(years)
        return [sorted(years[i::k]) for i in range(k)]

    def crossvalidate(self, years, how, ignore_estimation_error=False, splitter=None, **kwargs):
        years = self._years(years)
        if not splitter:
            #splitter = self._splitter_leave_n_out
            splitter = self._splitter_k_fold
            #splitter = lambda years: self._splitter_k_fold(years, k=5)
        validate_years_list = splitter(years)

        def metric(validate_years):
            calibrate_years = sorted(set(years) - set(validate_years))
            try:
                coeff = self._coeffs[tuple(calibrate_years)]
            except:
                coeff = self.calibrate(calibrate_years, save=False, **kwargs)
            return self.metric(validate_years, how, coeff, ignore_estimation_error)
        cv = np.ma.array([metric(v) for v in validate_years_list])
        if cv.dtype == np.object:
            cv = np.concatenate(cv)
        cv.set_fill_value(np.nan)
        return cv.flatten()

    def analyze_sensitivity(self, years, deltas):
        years = self._years(years)
        def estimate(delta):
            try:
                self._mets = self._dataset.weather() + delta
                return self.estimates(years, julian=True)
            finally:
                self._mets = self._dataset.weather()
        o = estimate(0)
        p_list = np.ma.array([estimate(d) for d in deltas])
        return (p_list - o).mean(axis=1)
