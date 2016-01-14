from __future__ import division

from .base import Estimator

import numpy as np
import pandas as pd

class BetaFunc(Estimator):
    @property
    def name(self):
        return 'Beta'

    @property
    def coeff_names(self):
        return [
            'Ds', # start date (days offset)
            'Tx', # maximum temperature (C)
            'To', # optimum temperature (C)
            'Rg', # growth requirement
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (1, 35, 20, 50),
            'bounds': ((-100, 100), (20, 60), (0, 40), (0, 200)),
            'grid': (slice(-100, 100, 1), slice(20, 60, 0.5), slice(0, 40, 0.5), slice(0, 200, 1)),
        }

    def _estimate(self, year, met, coeff):
        T = met.tavg
        Tn, To, Tx = 0, coeff['To'], coeff['Tx']
        if not Tn < To < Tx:
            raise EstimationError("temperature out of order: Tn='{}' < To='{}' < Tx='{}'".format(Tn, To, Tx))

        Txu = Tx - T
        Txl = Tx - To
        Tnu = T - Tn
        Tnl = To - Tn
        c = (To - Tn) / (Tx - To)
        r = (Txu/Txl)*(Tnu/Tnl).pow(c).fillna(0)
        g = r.clip(lower=0) / 24

        aux = pd.concat({
            'r': r,
            'g': g,
            'Cg': g.cumsum(),
        }, axis=1)

        return self._match(aux['Cg'], coeff['Rg'])
