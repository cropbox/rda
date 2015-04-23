from estimation import Estimator

import numpy as np
import pandas as pd

class BetaFunc(Estimator):
    @property
    def name(self):
        return 'BetaFunc'

    @property
    def coeff_names(self):
        return [
            'Ds', # start date (Julian)
            'Tx', # maximum temperature (C)
            'To', # optimum temperature (C)
            'Rg', # growth requirement
        ]

    @property
    def default_options(self):
        return {
            #'coeff0': (35, 20, 50),
            #'bounds': ((20, 50), (10, 40), (0, 200)),
            #'grid': (slice(30, 60, 0.5), slice(15, 35, 0.5), slice(10, 100, 1)),
            'coeff0': (1, 35, 20, 50),
            'bounds': ((-100, 100), (20, 60), (0, 40), (0, 200)),
            'grid': (slice(-100, 100, 1), slice(20, 60, 0.5), slice(0, 40, 0.5), slice(0, 200, 1)),
        }

    def _estimate(self, year, met, coeff):
        T = met.tavg
        Tx, To = coeff['Tx'], coeff['To']
        Rx = 1.
        Tn = 0.
        Txu = (Tx - T)*1.
        Txl = (Tx - To)*1.
        Tnu = (T - Tn)*1.
        Tnl = (To - Tn)*1.
        c = (To - Tn) / ((Tx - To)*1.)
        r = Rx * (Txu/Txl)*(Tnu/Tnl).pow(c).fillna(0)
        g = r.clip(lower=0) * (1 / 24.)

        aux = pd.concat({
            'r': r,
            'g': g,
            'Cg': g.cumsum(),
        }, axis=1)

        return self._match(aux['Cg'], coeff['Rg'])
