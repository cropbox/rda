import numpy as np
import scipy.optimize
import pandas as pd
import datetime

class EstimationError(Exception):
    pass

class Estimator(object):
    def __init__(self, mets, obss, coeff=None):
        self._mets = mets
        self._obss = obss
        self._coeff = coeff
        self.setup()

    @property
    def name(self):
        return str(self.__class__.__name__)

    @property
    def coeff_names(self):
        return []

    @property
    def default_options(self):
        return {
            'coeff0': {},
            'bounds': (),
            'grid': (),
            'fixed_coeff': {}
        }

    def setup(self):
        pass

    # date range
    def start_date(self, year, coeff):
        try:
            #return datetime.datetime.strptime('{}-{}'.format(year, int(coeff['Ds'])), '%Y-%j')
            jday = int(coeff['Ds']) - 1
            return datetime.date(year, 1, 1) + datetime.timedelta(days=jday)
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
        if years is None:
            start = int(max(self._mets.index[0].year, self._obss.index[0]))
            end = int(min(self._mets.index[-1].year, self._obss.index[-1]))
            return range(start, end+1)
        #HACK support (start, end) tuple for convenience
        elif type(years) is tuple and len(years) == 2:
            start, end = years
            return range(start, end+1)
        elif type(years) is int:
            return [years]
        else:
            return years

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

    # estimation
    def _match(self, ts, value):
        i = ts.fillna(0).searchsorted(value)[0]
        try:
            return ts.index[i]
        except:
            raise EstimationError("requirement '{}' cannot be matched".format(value))

    def _estimate(self, year, met, coeff):
        #FIXME: raise NotImplementedError?
        return self._match(met.ix[:, -1], 1.0)

    def estimate(self, year, coeff=None):
        if coeff is None:
            coeff = self._coeff
        else:
            coeff = self._normalize(coeff)
        try:
            met = self._clip(year, coeff)
        except:
            #FIXME DC weather data missing for 2007-02
            #return None
            raise EstimationError("weather cannot be clipped for '{}'".format(year))
        return self._estimate(year, met, coeff).to_datetime()

    def estimates(self, years, coeff=None):
        def estimate_safely(y):
            try:
                return self.estimate(y, coeff)
            except:
                return None
        years = self._years(years)
        return [estimate_safely(y) for y in years]

    def estimate_multi(self, year, coeffs=None):
        if coeffs is None:
            coeffs = self._coeffs
        else:
            coeffs = [self._normalize(c) for c in coeffs]

        def estimate(c):
            try:
                return self._estimate(year, self._clip(year, c), c).to_datetime().strftime('%j')
            except:
                return None
        ests = [estimate(c) for c in coeffs]
        return pd.Series(ests).dropna().astype(int)

    def estimate_multi2(self, year, coeffs=None):
        if coeffs is None:
            coeffs = self._coeffs
        else:
            coeffs = [self._normalize(c) for c in coeffs]

        def estimate(c):
            try:
                return self._estimate(year, self._clip(year, c), c).to_datetime()
            except:
                return None
        ests = [estimate(c) for c in coeffs]
        return pd.Series(ests).value_counts().sort_index().resample('D', 'sum').dropna().astype(int)

    # observation
    def observe(self, year):
        return self._obss.loc[year].to_datetime().replace(hour=12)

    # calibration
    def _calibrate(self, years, disp=True, **kwargs):
        opts = dict(self.default_options)
        opts.update(kwargs)

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
            return self.error(years, 'rmse', coeff)

        # new default to 'differential evolution'
        if not opts.has_key('method'):
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
        self._coeff = self._calibrate(years, disp, **kwargs)
        return self._coeff

    # validation
    def residual(self, year, coeff=None):
        try:
            est = self.estimate(year, coeff)
            obs = self.observe(year)
            sec_per_day = 60*60*24.
            return (est - obs).total_seconds() / sec_per_day
            #return (est - obs).days
        except EstimationError:
            return 365.
            #return np.inf

    def error(self, years, how='rmse', coeff=None):
        years = self._years(years)
        e = np.array([self.residual(y, coeff) for y in years])

        how = how.lower()
        if how == 'residual':
            return e
        elif how == 'rmse':
            return np.sqrt(np.mean(e**2))
        elif how == 'mae':
            return np.mean(e)
        elif how == 'xe':
            return np.max(e)
