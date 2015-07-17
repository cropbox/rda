from .base import Estimator

import numpy as np
import pandas as pd
import datetime
import itertools
import collections

class Ensemble(Estimator):
    def setup(self):
        self.estimators = []
        self.nick = None

    @property
    def name(self):
        if self.nick:
            return self.nick
        else:
            return super(Ensemble, self).name

    @property
    def coeff_names(self):
        return ['W', 'C']

    @property
    def coeff(self):
        c = zip(['w{}'.format(i) for i in range(self.n)], self._coeff['W'])
        return collections.OrderedDict(c)

    @property
    def default_options(self):
        return {
            'W': [1. / self.n] * self.n,
            'C': [m._coeff for m in self.estimators],
        }

    @property
    def n(self):
        return len(self.estimators)

    def use(self, estimators, years, nick=None, how=None):
        self.estimators = estimators
        self.nick = nick
        self.how = how
        self.calibrate(years)
        return self

    def _calibrate(self, years, disp=True, **kwargs):
        opts = self.options(**kwargs)

        def weight(m):
            if self.how:
                e = m.metric(years, self.how)
                if self._is_higher_better(self.how):
                    return e
                else:
                    return 1./e
            else:
                return 1.
        W = np.array([weight(m) for m in self.estimators])
        W = (W / sum(W)).tolist()
        coeff = self._dictify([W, opts['C']])
        return coeff

    def _estimate(self, year, met, coeff):
        o = datetime.datetime(year, 1, 1)
        d = [m.estimate_safely(year, c, julian=True) for (m, c) in zip(self.estimators, coeff['C'])]
        d = np.ma.masked_values(d, self._mask(julian=True))
        w = np.ma.array(coeff['W'], mask=d.mask)
        w = w / w.sum()
        t = o + datetime.timedelta(days=np.sum(w*d) - 1)
        return pd.Timestamp(t)

    def _estimate_multi(self, calibrate_years, estimate_year, julian=False):
        coeff_backup = self._coeff.copy(), self._coeffs.copy()

        key = tuple(calibrate_years)
        C = [m._coeffs[key] for m in self.estimators]
        self.calibrate(calibrate_years, C=C)

        est = self.estimate_safely(estimate_year, julian=julian)

        self._coeff, self._coeffs = coeff_backup
        return est

    def estimate_multi(self, year, coeffs=None, julian=False):
        #years = self._years(self._calibrate_years)
        #calibrate_yearss = [list(x) for x in itertools.combinations(years, len(years)-n)]
        #TODO avoid self.estimators[0]... use self._coeffs to hold keys?
        calibrate_yearss = [list(x) for x in self.estimators[0]._coeffs.keys()]
        s = [self._estimate_multi(y, year, julian) for y in calibrate_yearss]
        ests = np.ma.masked_values(s, self._mask(julian))
        return pd.Series(ests).dropna()

    def metric_with_calibration(self, calibrate_years, validate_years, how='e'):
        coeff_backup = self._coeff.copy(), self._coeffs.copy()

        key = tuple(calibrate_years)
        C = [m._coeffs[key] for m in self.estimators]
        self.calibrate(calibrate_years, C=C)

        metrics = self.metric(validate_years, how)

        self._coeff, self._coeffs = coeff_backup
        return metrics

    def crossvalidate(self, years, how='e', ignore_estimation_error=False, n=1):
        years = self._years(years)
        calibrate_yearss = [list(x) for x in itertools.combinations(years, len(years)-n)]
        def metric(y):
            validate_years = sorted(set(years) - set(y))
            return self.metric_with_calibration(y, validate_years, how)
        return np.array([metric(y) for y in calibrate_yearss])
