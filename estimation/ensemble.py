from estimation import Estimator

import numpy as np
import pandas as pd
import datetime
import itertools

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
    def default_options(self):
        return {
            'W': [1. / self.n] * self.n,
            'C': [m._coeff for m in self.estimators],
        }

    @property
    def n(self):
        return len(self.estimators)

    def use(self, estimators, years, nick=None, weighted=True):
        self.estimators = estimators
        self.nick = nick
        self.weighted = weighted
        self.calibrate(years)

    def _calibrate(self, years, disp=True, **kwargs):
        opts = self.options(**kwargs)

        def weight(m):
            if self.weighted:
                return 1. / m.error(years, 'rmse')
            else:
                return 1.
        W = np.array([weight(m) for m in self.estimators])
        W = W / sum(W)
        coeff = self._dictify([W, opts['C']])
        return coeff

    def _estimate(self, year, met, coeff):
        o = datetime.datetime(year, 1, 1)
        d = [m.estimate(year, c, julian=True) for (m, c) in zip(self.estimators, coeff['C'])]
        w = np.array(coeff['W'])
        t = o + datetime.timedelta(days=np.sum(w*d) - 1)
        return pd.Timestamp(t)

    def error_with_calibration(self, calibrate_years, validate_years, how='e'):
        coeff_backup = self._coeff.copy(), self._coeffs.copy()

        calibrate_years = self._years(calibrate_years)
        validate_years = self._years(validate_years)

        key = tuple(calibrate_years)
        C = [m._coeffs[key] for m in self.estimators]
        self.calibrate(calibrate_years, C=C)

        errors = self.error(validate_years, how)

        self._coeff, self._coeffs = coeff_backup
        return errors

    def crossvalidate(self, years, how='e', n=1):
        years = self._years(years)
        calibrate_yearss = [list(x) for x in itertools.combinations(years, len(years)-n)]
        return np.array([self.error_with_calibration(y, years, how) for y in calibrate_yearss])
