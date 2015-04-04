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
            #'Ds', # start date (Julian)
            'Tb', # base temperature (C)
            'Rd', # GDD accumulation requirement
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (4.5, 250),
            'grid': (slice(2, 7, 0.1), slice(200, 400, 5)),
        }

    def _estimate(self, year, met, coeff):
        tbase = coeff['Tb']
        tdd = (met.tavg - tbase).clip(lower=0) / 24.
        aux = pd.concat({
            'Dd': tdd,
            'Cd': tdd.cumsum(),
        }, axis=1)
        return self._match(aux['Cd'], coeff['Rd'])
