from .base import Estimator, EstimationError

import numpy as np
import pandas as pd
import datetime

class ChillingForce(Estimator):
    @property
    def name(self):
        return 'CF'

    @property
    def coeff_names(self):
        return [
            'Tc', # base temperature (C)
            'Rc', # chilling requirement
            'Rh', # heating requirement
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (4.5, -200, 300),
            'bounds': ((0, 10), (-400, -0), (0, 400)),
            'grid': (slice(0, 10, 0.1), slice(-400, -0, 1), slice(0, 400, 1)),
        }

    def start_date(self, year, coeff):
        # fix the start date as June 1st
        return datetime.date(year-1, 6, 1)

    def _aux(self, year, met, coeff):
        T = met.tavg
        Tc = coeff['Tc']
        tdd = (T - Tc).clip(lower=-Tc) / 24.

        # daily chill / heat (anti-chill) units
        return pd.concat({
            'Dc': tdd.clip(upper=0),
            'Dh': tdd.clip(lower=0),
        }, axis=1)

    def _estimate(self, year, met, coeff):
        aux = self._aux(year, met, coeff)

        # dormancy release
        aux['DR'] = aux['Dc'].cumsum() / coeff['Rc']
        try:
            awakening = self._match(aux['DR'], 1.0)
        except EstimationError:
            # force dormancy break when spring comes
            awakening = pd.to_datetime(pd.datetime(year, 3, 1))

        # flower development
        aux['FD'] = aux[awakening:]['Dh'].cumsum() / coeff['Rh']
        return self._match(aux['FD'], 1.0)
