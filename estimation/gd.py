from .base import Estimator

import datetime
import numpy as np
import pandas as pd
import multiprocessing as mp

class GrowingDegree(Estimator):
    @property
    def name(self):
        return 'GD'

    @property
    def coeff_names(self):
        return [
            'Ds', # start date (Julian)
            'Tb', # base temperature (C)
            'Rd', # accumulation requirement
        ]

    @property
    def default_options(self):
        return {
            'coeff0': (1, 4.5, 250),
            'bounds': ((-100, 100), (0, 10), (0, 1000)),
            'grid': (slice(-100, 100, 1), slice(0, 10, 0.1), slice(0, 1000, 1)),
        }

    def _calculate(self, year, met, coeff):
        tbase = coeff['Tb']
        tdd = (met.tavg - tbase).clip(lower=0) / 24.
        return tdd

    def _estimate(self, year, met, coeff):
        tdd = self._calculate(year, met, coeff)
        aux = pd.concat({
            'Dd': tdd,
            'Cd': tdd.cumsum(),
        }, axis=1)
        return self._match(aux['Cd'], coeff['Rd'])

    def _preset_func(self, x):
        df, year, Dss, Tbs, Rd_max = x

        def series(year, Ds, Tb):
            start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Ds)
            end_date = datetime.date(year, 5, 31)
            s = df.loc[start_date:end_date][Tb]
            s = s - s.iloc[0]
            s = s.apply(np.floor).astype(int)
            return s

        def tab(Ds, Tb):
            s = series(year, Ds, Tb)
            s = s[s <= Rd_max].drop_duplicates().reset_index()
            est = s['timestamp'].apply(lambda t: self._julian(t, year))
            obs = self.observe(year, julian=True)
            diff = obs - est
            sq = diff**2
            return pd.DataFrame({'Ds': Ds, 'Tb': Tb, 'Rd': s[Tb], 'year': year, 'sq': sq})
        return pd.concat([tab(Ds, Tb) for Ds in Dss for Tb in Tbs])

    def _preset(self, years, **kwargs):
        years = self._years(years)
        opts = self.options(**kwargs)

        grids = dict(zip(self.coeff_names, opts['grid']))

        def slice_to_range(s):
            return np.arange(s.start, s.stop + s.step, s.step).tolist()

        Dss = slice_to_range(grids['Ds'])
        Tbs = slice_to_range(grids['Tb'])
        Rd_max = grids['Rd'].stop

        tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        Dds = pd.concat(tdds, axis=1)
        Cds = Dds.cumsum()

        def subdata(df, year):
            return df.loc[str(year-1):str(year+1)]

        argss = [(subdata(Cds, year), year, Dss, Tbs, Rd_max) for year in years]
        pool = mp.Pool()
        res = pool.map(self._preset_func, argss)
        pool.close()
        pool.join()
        return pd.concat(res)


class GrowingDegreeDay(GrowingDegree):
    @property
    def name(self):
        return 'GDD'

    def _calculate(self, year, met, coeff):
        T = met.tavg.resample('D', how={'tmax': np.max, 'tmin': np.min})
        tbase = coeff['Tb']
        tdd = ((T.tmax + T.tmin) / 2. - tbase).clip(lower=0)
        tdd = tdd.resample('H', fill_method='ffill') / 24.
        return tdd
