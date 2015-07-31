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
        T = met.tavg.clip(lower=0)
        Tc = coeff['Tc']
        tdd = (T - Tc) / 24.

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


class ChillingForceDay(ChillingForce):
    @property
    def name(self):
        return 'CFD'

    def _aux(self, year, met, coeff):
        T = met.tavg.resample('D', how={
            'x': np.max,
            'n': np.min,
            'M': np.mean,
        })
        Tc = coeff['Tc']

        def chill(t):
            Cd = 0
            if 0 <= Tc <= t.n <= t.x:
                Cd = 0
            elif 0 <= t.n <= Tc < t.x:
                Cd = -((t.M - t.n) - (t.x - Tc)**2 / (2*(t.x - t.n)))
            elif 0 <= t.n <= t.x <= Tc:
                Cd = -(t.M - t.n)
            elif t.n < 0 <= t.x <= Tc:
                Cd = -(t.x**2 / (2*(t.x - t.n)))
            elif t.n < 0 < Tc <= t.x:
                Cd = -(t.x**2 / (2*(t.x - t.n))) - (t.x - Tc)**2 / (2*(t.x - t.n))
            return Cd

        def anti_chill(t):
            Ca = 0
            if 0 <= Tc <= t.n <= t.x:
                Ca = t.M - Tc
            elif 0 <= t.n <= Tc < t.x:
                Ca = (t.x - Tc)**2 / (2*(t.x - t.n))
            elif 0 <= t.n <= t.x <= Tc:
                Ca = 0
            elif t.n < 0 <= t.x <= Tc:
                Ca = 0
            elif t.n < 0 < Tc <= t.x:
                Ca = (t.x - Tc)**2 / (2*(t.x - t.n))
            return Ca

        def unit(f):
            return T.apply(f, axis=1).resample('H', fill_method='ffill') / 24.

        # daily chill / heat (anti-chill) units
        return pd.concat({
            'Dc': unit(chill),
            'Dh': unit(anti_chill),
        }, axis=1)
