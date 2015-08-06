from .base import Estimator

import numpy as np
import pandas as pd
import datetime

class Mean(Estimator):
    @property
    def name(self):
        return 'M'

    @property
    def coeff_names(self):
        return [
            'Do', # mean observation date (days offset)
        ]

    @property
    def default_options(self):
        return {}

    def _calibrate(self, years, disp=True, **kwargs):
        # save mean observation date as an offset to the first day of year
        o = np.mean(self.observes(years, julian=True)) - 1
        coeff = self._dictify([o])
        return coeff

    def _estimate(self, year, met, coeff):
        t = datetime.datetime(year, 1, 1) + datetime.timedelta(days=coeff['Do'])
        return pd.Timestamp(t)
