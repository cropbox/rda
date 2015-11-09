from .base import Estimator

import numpy as np
import pandas as pd

class StandardTemperature(Estimator):
    @property
    def name(self):
        return 'DTS'

    @property
    def coeff_names(self):
        return [
            #'Ds', # start date (days offset)
            'Ts', # standard temperature (C)
            'Ea', # temperature sensitivity rate (kJ mol-1)
            'Rd', # standard temperature accumulation requirement
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (1, 15, 20, 200),
            #'bounds': ((-100, 100), (-10, 30), (0, 200), (0, 500)),
            'bounds': ((-10, 30), (0, 200), (0, 500)),
            'grid': (slice(-100, 100, 1), slice(-10, 30, 1), slice(0, 200, 1), slice(0, 500, 1)),
        }

    def _estimate(self, year, met, coeff):
        Ea = coeff['Ea']
        #T = met.tavg.resample('D') + 273.15
        T = met.tavg.resample('H') + 273.15
        #Ts = 271.4 # standard temperature (K)
        Ts = coeff['Ts'] + 273.15
        R = 8.314 # gas constant (J K-1 mol-1)
        dts = np.exp(Ea * 1000. * (T - Ts) / (R * T * Ts))
        #dts = dts.resample('H', fill_method='ffill')
        dts = dts / 24.
        aux = pd.concat({
            'Dd': dts,
            'Cd': dts.cumsum(),
        }, axis=1)
        return self._match(aux['Cd'], coeff['Rd'])
