from .base import Estimator, EstimationError

import numpy as np
import pandas as pd
import datetime

# Nizinski and Saugier, 1988
# Fu et al., 2012
class ThermalPeriod(Estimator):
    @property
    def name(self):
        return 'TP'

    @property
    def coeff_names(self):
        return [
            'Tb', # base temperature (C)
            'Dn', # fixed period (days)
            'Rd', # forcing threshold
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (5, 50, 500),
            'bounds': ((0, 10), (30, 100), (0, 1000)),
            'grid': (slice(0, 10, 0.1), slice(30, 100, 1), slice(0, 1000, 1)),
        }

    def start_date(self, year, coeff):
        # fix initial starting date for thermal period to be February 1st
        return datetime.date(year, 2, 1)

    def _estimate(self, year, met, coeff):
        Tb = coeff['Tb']
        units = (met.tavg - Tb).clip(lower=0) / 24

        Dn = coeff['Dn']
        offset = datetime.timedelta(days=int(Dn))
        Rd = coeff['Rd']

        # def check(sd, ld):
        #     f = units.loc[sd:ld].sum()
        #     return f >= Rd
        #
        # for d in units.index:
        #     ld = d + offset
        #     if check(d, ld):
        #         return ld
        #raise EstimationError("requirement '{}' cannot be matched in '{}' days".format(Rd, Dn))

        sd = pd.Timestamp(self.start_date(year, coeff))
        ld = sd + offset
        ed = pd.Timestamp(self.end_date(year, coeff))
        ad = datetime.timedelta(days=1)

        def unit(a, b):
            return units.loc[a:b].sum() - units.loc[b]

        def error():
            raise EstimationError("requirement '{}' cannot be matched for '{}' days".format(Rd, Dn))

        if ld > ed:
            error()
        f = unit(sd, ld)
        if f >= Rd:
            return ld

        while True:
            sd2, ld2 = sd + ad, ld + ad
            if ld2 > ed:
                error()
            f -= unit(sd, sd2)
            f += unit(ld, ld2)
            sd, ld = sd2, ld2
            if f >= Rd:
                return ld
