from .ensemble import Ensemble

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import pickle
import datetime

class RandomForest(Ensemble):
    @property
    def coeff_names(self):
        return ['p', 'C']

    @property
    def default_options(self):
        return {
            'p': None,
            'C': [m._coeff for m in self.estimators],
        }

    def _calibrate(self, years, disp=True, **kwargs):
        opts = self.options(**kwargs)

        X = np.ma.array([m.estimates(years, julian=True) for m in self.estimators]).T
        y = self.observes(years, julian=True)
        clf = RandomForestRegressor(n_estimators=1000, random_state=0)
        clf = clf.fit(X, y)
        self._regressor = clf

        p = pickle.dumps(clf)
        coeff = self._dictify([p, opts['C']])
        return coeff

    def _estimate(self, year, met, coeff):
        o = datetime.datetime(year, 1, 1)
        X = [m.estimate_safely(year, c, julian=True) for (m, c) in zip(self.estimators, coeff['C'])]
        X = np.ma.masked_values(X, self._mask(julian=True))
        X = X.filled(X.mean()).reshape(1, -1)
        d = self._regressor.predict(X).item()
        t = o + datetime.timedelta(days=d-1)
        return pd.Timestamp(t)
