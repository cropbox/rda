from estimation import Estimator

import numpy as np
import pandas as pd

class Dts(Estimator):
    @property
    def name(self):
        return 'DTS'

    @property
    def coeff_names(self):
        return [
            #'Ds', # start date (Julian)
            'Ea', # temperature sensitivity rate (kJ mol-1)
            'Rd', # standard temperature accumulation requirement
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (20, 200),
            'grid': (slice(10, 100, 1), slice(100, 300, 1)),
        }

    def _estimate(self, year, met, coeff):
        Ea = coeff['Ea']
        #T = met.tavg.resample('D') + 273.15
        T = met.tavg.resample('H') + 273.15
        Ts = 271.4 # standard temperature (K)
        R = 8.314 # gas constant (J K-1 mol-1)
        dts = np.exp(Ea * 1000. * (T - Ts) / (R * T * Ts))
        #dts = dts.resample('H', fill_method='ffill')
        aux = pd.concat({
            'Dd': dts,
            'Cd': dts.cumsum() / 24.,
        }, axis=1)
        return self._match(aux['Cd'], coeff['Rd'])
