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
            'Rd', # adjustment for heating requirement (Rh = -Rc + Rd)
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (4.5, -200, 100),
            'bounds': ((0, 10), (-350, -50), (0, 200)),
            'grid': (slice(0, 10, 0.1), slice(-350, -50, 1), slice(0, 200, 1)),
        }

    def start_date(self, year, coeff):
        # fix the start date as June 1st
        return datetime.date(year-1, 6, 1)

    def _degrees(self, year, met, coeff):
        T = met.tavg.clip(lower=0)
        Tc = coeff['Tc']
        units = (T - Tc) / 24.

        # daily chill / heat (anti-chill) units
        return pd.concat({
            'Dc': units.clip(upper=0),
            'Dh': units.clip(lower=0),
        }, axis=1)

    def _estimate(self, year, met, coeff):
        D = self._degrees(year, met, coeff)
        chill = D['Dc']
        heat = D['Dh']

        # rest & quiescence ends = dormancy release = bud burst
        Rc = coeff['Rc']
        try:
            rest = chill.cumsum()
            #HACK _match() assumes pre-sorted ascending order
            awakening = self._match(rest, Rc, descending=True)
            quiescence = heat.loc[awakening:].cumsum()
            budding = self._match(quiescence, -Rc)
        except EstimationError as e:
            #HACK immature calibration with forced dormancy break
            # force dormancy release when spring comes
            #awakening = pd.NaT
            #budding = pd.to_datetime(pd.datetime(year, 3, 1))
            raise e

        # development after bud burst
        Rd = coeff['Rd']
        development = heat.loc[budding:].cumsum()
        flowering = self._match(development, Rd)
        return flowering


class ChillingForceDay(ChillingForce):
    @property
    def name(self):
        return 'CFD'

    def _degrees(self, year, met, coeff):
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
