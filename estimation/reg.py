from .base import Estimator

import numpy as np
import pandas as pd
import statsmodels.api as sm
import datetime

class MonthlyRegressor(Estimator):
    def setup(self):
        self.month = 0

    @property
    def coeff_names(self):
        return [
            'b0', # intercept
            'b1', # slope
        ]

    @property
    def default_options(self):
        return {}

    def _calibrate(self, years, disp=True, **kwargs):
        opts = self.options(**kwargs)

        met = pd.concat([self._mets.loc['%d' % y] for y in years])
        T = met.tavg.resample('M')
        X = T[T.index.month == self.month].dropna()
        X = sm.add_constant(X)
        Y = self._obss.loc[years].apply(lambda x: int(x.strftime('%j')))
        X.index = Y.index
        m = sm.OLS(Y, X).fit()

        if disp:
            print(m.summary())

        coeff = self._dictify(m.params)
        return coeff

    def _estimate(self, year, met, coeff):
        T = met.tavg.resample('M')
        Ti = T.index
        x = T[(Ti.year == year) & (Ti.month == self.month)]
        y = coeff['b0'] + coeff['b1']*x
        return pd.Timestamp(datetime.datetime.strptime('{}-{}'.format(year, int(round(y))), '%Y-%j').replace(hour=12))


class February(MonthlyRegressor):
    def setup(self):
        self.month = 2


class March(MonthlyRegressor):
    def setup(self):
        self.month = 3
