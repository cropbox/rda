from .base import Estimator, EstimationError

import numpy as np
import pandas as pd
import datetime

# Murray et al., 1989
# Fu et al., 2012
class AlternatingModel(Estimator):
    @property
    def name(self):
        return 'AM'

    @property
    def coeff_names(self):
        return [
            'Tb', # base temperature (C)
            'Tc', # chilling temperature (C)
            'Fa', # fitting parameter for forcing
            'Fb', # fitting parameter for forcing
            'Fr', # fitting parameter for forcing
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (4.5, 4.5, 0, 500, 0),
            'bounds': ((0, 20), (-10, 10), (-1000, 1000), (100, 2000), (-1, 1)),
            'grid': (slice(0, 20, 0.1), slice(-10, 10, 0.1), slice(-1000, 1000, 10), slice(100, 2000, 10), slice(-1, 1, 0.1)),
        }

    def start_date(self, year, coeff):
        # fix chilling start date to be October 1st
        return datetime.date(year-1, 10, 1)

    def _forcing_start_date(self, year, coeff):
        # fix forcing start date to be January 1st
        return datetime.date(year, 1, 1)

    def _estimate(self, year, met, coeff):
        T = met.tavg

        Tc = coeff['Tc']
        Rc = (T <= Tc).cumsum()

        a = coeff['Fa']
        b = coeff['Fb']
        r = coeff['Fr']
        Rf = a + b * np.exp(r * Rc)

        Tb = coeff['Tb']
        sd = self._forcing_start_date(year, coeff)
        F = (T[sd:] - Tb).clip(lower=0) / 24
        aux = pd.concat({
            'Dd': F,
            'Cd': F.cumsum(),
        }, axis=1)
        return self._match(aux['Cd'] - Rf, 0)
