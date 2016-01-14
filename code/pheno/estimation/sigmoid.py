from .base import Estimator

import numpy as np
import pandas as pd

# Fu et al., 2012
class SigmoidFunc(Estimator):
    @property
    def name(self):
        return 'SF'

    @property
    def coeff_names(self):
        return [
            'Ds', # start date (days offset)
            'Tb', # base temperature (C)
            'St', # temperature sensitivity (C-1)
            'Rd', # temperature accumulation requirement
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (1, 15, -0.1, 100),
            'bounds': ((-100, 100), (-10, 20), (-1.0, -0.1), (0, 200)),
            'grid': (slice(-100, 100, 1), slice(-10, 30, 1), slice(-1.0, -0.1, 0.05), slice(0, 200, 1)),
        }

    def _estimate(self, year, met, coeff):
        Tb = coeff['Tb']
        St = coeff['St']
        def f(T):
            return 1 / (1 + np.exp(St * (T - Tb)))
        units = f(met.tavg).clip(lower=f(0)) / 24
        aux = pd.concat({
            'Dd': units,
            'Cd': units.cumsum(),
        }, axis=1)
        return self._match(aux['Cd'], coeff['Rd'])
