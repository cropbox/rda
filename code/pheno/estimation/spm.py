from .base import Estimator, EstimationError

import numpy as np
import pandas as pd
import datetime

# Sarvas, 1974
# Hanninen, 1990
# Kramer, 1994
# Fu et al., 2012
class SequentialModel(Estimator):
    @property
    def name(self):
        return 'SM'

    @property
    def coeff_names(self):
        return [
            # 'Tn', # chilling minimum temperature (C)
            # 'To', # chilling optimum temperature (C)
            # 'Tx', # chilling maximum temperature (C)
            'To', # chilling optimum temperature (C)
            'Tnd', # chilling minimum temperature (C)
            'Txd', # chilling maximum temperature (C)
            'Rc', # chilling requirement
            'Tb', # base temperature (C)
            'St', # temperature sensitivity (C-1)
            'Rf', # forcing requirement
        ]

    @property
    def default_options(self):
        return {
            # 'coeff0': (-3, 3, 10, 200, 15, -0.1, 200),
            # 'bounds': ((-10, 5), (-5, 10), (0, 15), (1, 500), (0, 30), (-1.0, -0.1), (1, 500)),
            # 'grid': (slice(-10, 5, 0.1), slice(-5, 10, 0.1), slice(0, 15, 0.1), slice(1, 500, 1), slice(0, 30, 0.1), slice(-1.0, -0.1, 0.05), slice(1, 500, 1)),
            'coeff0': (5, 5, 5, 200, 15, -0.1, 200),
            'bounds': ((-5, 10), (1, 20), (1, 10), (1, 500), (0, 20), (-1.0, -0.1), (1, 500)),
            'grid': (slice(-5, 10, 0.1), slice(1, 20, 0.1), slice(1, 10, 0.1), slice(1, 500, 1), slice(0, 30, 0.1), slice(-1.0, -0.1, 0.05), slice(1, 500, 1)),
        }

    def start_date(self, year, coeff):
        # fix the start date as October 1st
        return datetime.date(year-1, 10, 1)

    def _chilling(self, met, coeff):
        T = met.tavg
        # Tn, To, Tx = coeff['Tn'], coeff['To'], coeff['Tx']
        # if not Tn < To < Tx:
        #     raise EstimationError("chilling temperature out of order: Tn='{}' < To='{}' < Tx='{}'".format(Tn, To, Tx))
        Tnd, To, Txd = coeff['Tnd'], coeff['To'], coeff['Txd']
        Tn = To - Tnd
        Tx = To + Txd

        Txu = Tx - T
        Txl = Tx - To
        Tnu = T - Tn
        Tnl = To - Tn
        c = (To - Tn) / (Tx - To)
        r = (Txu/Txl)*(Tnu/Tnl).pow(c).fillna(0)
        g = r.clip(lower=0) / 24
        return g

    def _forcing(self, met, coeff):
        T = met.tavg
        Tb = coeff['Tb']
        St = coeff['St']
        return 1 / (1 + np.exp(St * (T - Tb))) / 24

    def _degrees(self, met, coeff):
        return {
            'Dc': self._chilling(met, coeff),
            'Dh': self._forcing(met, coeff),
        }

    def _estimate(self, year, met, coeff):
        D = self._degrees(met, coeff)
        chill, heat = D['Dc'], D['Dh']

        # rest & quiescence ends = dormancy release = bud burst
        Rc = coeff['Rc']
        try:
            rest = chill.cumsum()
            awakening = self._match(rest, Rc)
        except EstimationError as e:
            #HACK immature calibration with forced dormancy break
            # force dormancy release when spring comes
            #awakening = pd.NaT
            #budding = pd.to_datetime(pd.datetime(year, 3, 1))
            raise e

        # development after bud burst
        Rf = coeff['Rf']
        development = heat.loc[awakening:].cumsum()
        flowering = self._match(development, Rf)
        return flowering


# Landsberg, 1974
# Hanninen, 1990
# Kramer, 1994
# Fu et al., 2012
class ParallelModel(SequentialModel):
    @property
    def name(self):
        return 'PM'

    @property
    def coeff_names(self):
        return super(ParallelModel, self).coeff_names + [
            'Km', # forcing weight coefficient
        ]

    @property
    def default_options(self):
        o = super(ParallelModel, self).default_options
        o['coeff0'] += (0.5,)
        o['bounds'] += ((0, 1),)
        o['grid'] += (slice(0, 1, 0.1),)
        return o

    def _degrees(self, met, coeff):
        D = super(ParallelModel, self)._degrees(met, coeff)
        chill, heat = D['Dc'], D['Dh']

        Rc = coeff['Rc']
        Km = coeff['Km']
        w = (chill.cumsum() / Rc).clip(upper=1)
        k = Km + (1 - Km)*w
        weighted_heat = k * heat

        return {
            'Dc': chill,
            'Dh': weighted_heat,
        }
