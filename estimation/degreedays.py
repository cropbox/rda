from estimation import Estimator

import numpy as np
import pandas as pd

class DegreeDays(Estimator):
    @property
    def name(self):
        return 'DegreeDays'

    @property
    def coeff_names(self):
        return [
            'Ds', # start date (Julian)
            'Tb', # base temperature (C)
            'Rd', # accumulation requirement
        ]

    @property
    def default_options(self):
        return {
            #'coeff0': (4.5, 250),
            #'bounds': ((0, 10), (0, 1000)),
            #'grid': (slice(3, 8, 0.1), slice(500, 1000, 5)),
            'coeff0': (1, 4.5, 250),
            'bounds': ((-100, 100), (0, 10), (0, 1000)),
            'grid': (slice(-100, 100, 1), slice(3, 8, 0.1), slice(500, 1000, 5)),
        }

    def _calculate(self, year, met, coeff):
        tbase = coeff['Tb']
        tdd = (met.tavg - tbase).clip(lower=0) / 24.
        return tdd

    def _estimate(self, year, met, coeff):
        tdd = self._calculate(year, met, coeff)
        aux = pd.concat({
            'Dd': tdd,
            'Cd': tdd.cumsum(),
        }, axis=1)
        return self._match(aux['Cd'], coeff['Rd'])


class GrowingDegreeDay(DegreeDays):
    @property
    def name(self):
        return 'GDD'

    def _calculate(self, year, met, coeff):
        T = met.tavg.resample('D', how={'tmax': np.max, 'tmin': np.min})
        tbase = coeff['Tb']
        tdd = ((T.tmax + T.tmin) / 2. - tbase).clip(lower=0)
        tdd = tdd.resample('H', fill_method='ffill') / 24.
        return tdd
