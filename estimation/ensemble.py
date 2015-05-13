from estimation import Estimator

import numpy as np
import pandas as pd
import statsmodels.api as sm
import datetime

class Ensemble(Estimator):
    def setup(self):
        self.estimators = []
        self.n = 0
        self.nick = None

    @property
    def name(self):
        if self.nick:
            return self.nick
        else:
            return super(Ensemble, self).name

    @property
    def coeff_names(self):
        return ['w{}'.format(i) for i in range(self.n)]

    @property
    def default_options(self):
        return {}

    def use(self, estimators, nick=None):
        self.estimators = estimators
        self.n = len(estimators)
        self._coeff = self.default_coeff()
        self.nick = nick

    def default_coeff(self):
        return self._dictify(np.ones(self.n) / self.n)

    def _calibrate(self, years, disp=True, **kwargs):
        w = [1. / m.error(years) for m in self.estimators]
        w = w / sum(w)
        coeff = self._dictify(w)
        return coeff

    #TODO just for testing
    def _calibrate_ols(self, years, disp=True, **kwargs):
        opts = self.options(**kwargs)

        def julian(t):
            try:
                return int(t.strftime('%j'))
            except:
                return np.nan

        X = np.array([[julian(t) for t in m.estimates(years)] for m in self.estimators]).transpose()
        X = sm.add_constant(X)
        Y = np.array([julian(t) for t in self.observes(years)]).transpose()
        lm = sm.OLS(Y, X)
        res = lm.fit()

        if disp:
            print res.summary()

        coeff = self._dictify(res.params)
        return coeff

    def _estimate(self, year, met, coeff):
        o = datetime.datetime(year, 1, 1)
        d = [(m.estimate(year) - o).total_seconds() for m in self.estimators]
        w = np.array(self._listify(self._coeff))
        t = o + datetime.timedelta(seconds=sum(w*d))
        return pd.Timestamp(t)
