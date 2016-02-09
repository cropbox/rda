from .ensemble import Ensemble

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import pickle
import base64
import datetime

class RandomForest(Ensemble):
    @property
    def coeff_names(self):
        return ['p', 'C']

    @property
    def default_options(self):
        return {
            'p': '',
            'C': [m._coeff for m in self.estimators],
        }

    def _calibrate(self, years, disp=True, **kwargs):
        opts = self.options(**kwargs)
        C = opts['C']

        X = np.ma.array([m.estimates(years, c, julian=True) for (m, c) in zip(self.estimators, C)]).T
        y = self.observes(years, julian=True)
        clf = RandomForestRegressor(n_estimators=1000, random_state=0)
        clf = clf.fit(X, y)
        p = base64.b64encode(pickle.dumps(clf)).decode('ascii')

        coeff = self._dictify([p, C])
        return coeff

    def _estimate(self, year, met, coeff):
        o = datetime.datetime(year, 1, 1)
        X = [m.estimate_safely(year, c, julian=True) for (m, c) in zip(self.estimators, coeff['C'])]
        X = np.ma.masked_values(X, self._mask(julian=True))
        X = X.filled(X.mean()).reshape(1, -1)
        clf = pickle.loads(base64.b64decode(coeff['p']))
        d = clf.predict(X).item()
        t = o + datetime.timedelta(days=d-1)
        return pd.Timestamp(t)


class RandomForest2(RandomForest):
    def _calibrate(self, years, disp=True, **kwargs):
        opts = self.options(**kwargs)
        C = opts['C']

        X = np.ma.array([m.estimates(years, c, julian=True) for (m, c) in zip(self.estimators, C)]).T
        y = self.observes(years, julian=True)
        #HACK feed some guiding points (e.g. [100, 100, ..., 100] -> 100)
        X = np.vstack([X, [[i+1]*self.n for i in range(366)]])
        y = np.hstack([y, [i+1 for i in range(366)]])
        clf = RandomForestRegressor(n_estimators=1000, random_state=0)
        clf = clf.fit(X, y)
        p = base64.b64encode(pickle.dumps(clf)).decode('ascii')

        coeff = self._dictify([p, C])
        return coeff
