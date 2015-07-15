from ..model.dataset import DataSet

import numpy as np
import scipy.optimize
import pandas as pd
import datetime
import itertools
import collections

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
        self._calibrate_years = None
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

    # date range
    def start_date(self, year, coeff):
        try:
            # use Ds as an offset (e.g. Ds = 0 indicates the first day of the year)
            offset = int(coeff['Ds'])
            return datetime.date(year, 1, 1) + datetime.timedelta(days=offset)
        except:
            return datetime.date(year-1, 10, 1)

    def end_date(self, year, coeff):
        return datetime.date(year, 5, 30)

    def _clip(self, year, coeff):
        t0 = datetime.datetime.combine(self.start_date(year, coeff), datetime.time(0))
        t1 = datetime.datetime.combine(self.end_date(year, coeff), datetime.time(23))
        df = self._mets[t0:t1]
        assert df.index[0] == t0, "start date '{}' != '{}'".format(df.index[0], t0)
        assert df.index[-1] == t1, "end date '{}' != '{}'".format(df.index[-1], t1)
        return df

    def _years(self, years):
        mety = self._mets.reset_index().timestamp.dt.year.unique()
        obsy = self._obss.reset_index().year.unique()
        defy = np.intersect1d(mety, obsy, assume_unique=True)

        def parse(y, allow_default=False):
            if allow_default and y is None:
                return defy.tolist()
            elif isinstance(y, tuple) and len(y) == 2:
                # support (start, end) tuple for convenience
                start, end = y
                return np.intersect1d(defy, range(start, end+1)).tolist()
            elif hasattr(y, '__iter__'):
                return sorted(set(sum([parse(i) for i in y], [])))
            elif isinstance(y, int):
                return [y] if y in defy else []
            else:
                raise ValueError("unrecognized format: years={}".format(years))
        return parse(years, allow_default=True)

    # coefficient
    def _listify(self, coeff, keys=None):
        if keys is None:
            keys = self.coeff_names
        if type(coeff) is list:
            return list(coeff)
        else:
            return list(coeff[k] for k in keys)

    def _dictify(self, values, keys=None, update={}):
        if keys is None:
            keys = self.coeff_names
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
    def _match(self, ts, value):
        i = ts.fillna(0).searchsorted(value)[0]
        try:
            return ts.index[i]
        except:
            raise EstimationError("requirement '{}' cannot be matched".format(value))

    def _estimate(self, year, met, coeff):
        #return self._match(met.ix[:, -1], 1.0)
        raise NotImplementedError

    def estimate(self, year, coeff=None, julian=False):
        if coeff is None:
            coeff = self._coeff
        else:
            coeff = self._normalize(coeff)
        try:
            met = self._clip(year, coeff)
        except:
            #HACK: allow masking for exceptions on missing data
            raise ObservationError("weather cannot be clipped for '{}'".format(year))
        t = self._estimate(year, met, coeff).to_datetime()
        if julian:
            return self._julian(t, year)
        else:
            return t

    def estimate_safely(self, years, coeff=None, julian=False):
        try:
            return self.estimate(years, coeff, julian)
        except:
            return self._mask(julian)

    def estimates(self, years, coeff=None, julian=False):
        s = [self.estimate_safely(y, coeff, julian) for y in self._years(years)]
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
            t = self._obss.loc[year].to_datetime().replace(hour=12)
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

    def observes(self, years, julian=False):
        s = [self.observe_safely(y, julian) for y in self._years(years)]
        return np.ma.masked_values(s, self._mask(julian))

    # calibration
    def _calibrate(self, years, disp=True, seed=1, **kwargs):
        opts = self.options(**kwargs)

        try:
            fixed_coeff = opts['fixed_coeff']
        except:
            fixed_coeff = {}
        coeff0 = self._dictify(opts['coeff0'])
        coeff_names = list(self.coeff_names)
        fixed_coeff_index = []
        for k in fixed_coeff:
            coeff0.pop(k)
            coeff_names.remove(k)
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

    def calibrate(self, years=None, disp=True, **kwargs):
        years = self._years(years)
        self._calibrate_years = years
        self._coeff = self._calibrate(years, disp, **kwargs)
        self._coeffs[''] = self._coeff
        return self._coeff

    # validation
    def residual(self, year, coeff=None):
        try:
            obs = self.observe(year, julian=True)
            est = self.estimate(year, coeff, julian=True)
            return est - obs
        except ObservationError:
            return RESIDUAL_OBSERVATION_ERROR
        except EstimationError:
            return RESIDUAL_ESTIMATION_ERROR
            #return np.inf

    @staticmethod
    def _is_higher_better(how):
        return how in {'ef', 'd', 'd1', 'dr'}

    def metric(self, years, how='e', coeff=None, ignore_estimation_error=False):
        years = self._years(years)
        #e = np.array([self.residual(y, coeff) for y in years])
        e = np.ma.masked_values([self.residual(y, coeff) for y in years], RESIDUAL_OBSERVATION_ERROR)

        if ignore_estimation_error:
            e = np.ma.masked_where(e == RESIDUAL_ESTIMATION_ERROR, e)

        how = how.lower()
        if how == 'e':
            return e
        elif how == 'rmse':
            return np.sqrt(np.mean(e**2))
        elif how == 'me':
            return np.mean(e)
        elif how == 'mae':
            return np.mean(np.abs(e))
        elif how == 'xe':
            return np.max(np.abs(e))

        # use calibrate_years, not input years
        obs_hat = self.observes(self._calibrate_years, julian=True).mean()
        d_est = self.estimates(years, coeff, julian=True) - obs_hat
        d_obs = self.observes(years, julian=True) - obs_hat

        if how == 'ef':
            return 1. - np.sum(e**2) / np.sum(d_obs**2)
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

    def crossvalidate(self, years, how, ignore_estimation_error=False, n=1):
        years = self._years(years)
        keys = list(itertools.combinations(years, len(years)-n))
        def metric(k):
            validate_years = sorted(set(years) - set(k))
            return self.metric(validate_years, how, self._coeffs[k], ignore_estimation_error)
        return np.array([metric(k) for k in keys])
