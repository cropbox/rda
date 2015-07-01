from .estimation import Estimator

import numpy as np
import pandas as pd

class ChillDay(Estimator):
    @property
    def name(self):
        return 'ChillDay'

    @property
    def coeff_names(self):
        return [
            'Ds', # start date (Julian)
            'Tc', # base temperature (C)
            'Rc', # chilling requirement
            'Rh', # heating requirement
        ]

    @property
    def default_options(self):
        return {
            #'coeff0': (4.5, -200, 300),
            #'bounds': ((0, 10), (0, 10), (-400, -100), (100, 400)),
            #'grid': (slice(2, 7, 0.1), slice(-300, -100, 5), slice(200, 400, 5)),
            'coeff0': (-92, 4.5, -200, 300),
            'bounds': ((-100, 0), (0, 10), (-400, -0), (0, 400)),
            'grid': (slice(-100, 0, 1), slice(0, 10, 0.1), slice(-400, -0, 1), slice(0, 400, 1)),
        }

    def _estimate(self, year, met, coeff):
        Tc = coeff['Tc']
        tdd = (met.tavg - Tc).clip(lower=-Tc) / 24.

        # daily chill / heat (anti-chill) units
        aux = pd.concat({
            'Dc': tdd.clip(upper=0),
            'Dh': tdd.clip(lower=0),
        }, axis=1)

        # dormancy release
        # no forced dormancy break even when spring comes
        aux['DR'] = aux['Dc'].cumsum() / coeff['Rc']
        awakening = self._match(aux['DR'], 1.0)

        # flower development
        aux['FD'] = aux[awakening:]['Dh'].cumsum() / coeff['Rh']
        return self._match(aux['FD'], 1.0)
