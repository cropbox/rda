from .base import Estimator

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

    def _preset_func_chill(self, x):
        df, year, Dss, Tcs, Rc_min = x

        def series(year, Ds, Tc):
            start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Ds)
            end_date = datetime.date(year, 5, 31)
            s = df.loc[start_date:end_date][Tc]
            s = s - s.iloc[0]
            s = s.apply(np.floor).astype(int)
            return s

        def tab(Ds, Tc):
            s = series(year, Ds, Tc)
            s = s[s >= Rc_min].drop_duplicates().reset_index()
            #FIXME: -1 to follow semantics of Ds offset
            Da = s['timestamp'].apply(lambda t: self._julian(t, year)).astype(int) - 1
            return pd.DataFrame({'Ds': Ds, 'Tc': Tc, 'Rc': s[Tc], 'Da': Da})
        return pd.concat([tab(Ds, Tc) for Ds in Dss for Tc in Tcs])

    def _preset_func_heat(self, x):
        df, year, Das, Tcs, Rh_max = x

        def series(year, Da, Tc):
            start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Da)
            end_date = datetime.date(year, 5, 31)
            s = df.loc[start_date:end_date][Tc]
            s = s - s.iloc[0]
            s = s.apply(np.floor).astype(int)
            return s

        def tab(Da, Tc):
            s = series(year, Da, Tc)
            s = s[s <= Rh_max].drop_duplicates().reset_index()
            est = s['timestamp'].apply(lambda t: self._julian(t, year))
            obs = self.observe(year, julian=True)
            diff = obs - est
            sq = diff**2
            return pd.DataFrame({'Da': Da, 'Tc': Tc, 'Rh': s[Tc], 'year': year, 'sq': sq})
        return pd.concat([tab(Da, Tc) for Da in Das for Tc in Tcs])

    def _preset(self, years, **kwargs):
        years = self._years(years)
        opts = self.options(**kwargs)

        grids = dict(zip(self.coeff_names, opts['grid']))

        def slice_to_range(s):
            return np.arange(s.start, s.stop + s.step, s.step).tolist()

        Dss = slice_to_range(grids['Ds'])
        Tcs = slice_to_range(grids['Tc'])
        Rc_min = grids['Rc'].start
        Rh_max = grids['Rh'].stop

        tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=-t) / 24. for t in Tcs]
        Dds = pd.concat(tdds, axis=1)
        Dcs = Dds.clip(upper=0)
        Dhs = Dds.clip(lower=0)
        Ccs = Dcs.cumsum()
        Chs = Dhs.cumsum()

        def subdata(df, year):
            return df.loc[str(year-1):str(year+1)]

        def chill(Ccs, years, Dss, Tcs, Rc_min):
            argss = [(subdata(Ccs, year), year, Dss, Tcs, Rc_min) for year in years]
            pool = mp.Pool()
            res = pool.map(self._preset_func_chill, argss)
            pool.close()
            pool.join()
            return res
        rescs = chill(Ccs, years, Dss, Tcs, Rc_min)

        def heat(Chs, years, resc, Tcs, Rh_max):
            argss = [(subdata(Chs, year), year, rescs[i].Da.unique(), Tcs, Rh_max) for i, year in enumerate(years)]
            pool = mp.Pool()
            res = pool.map(self._preset_func_heat, argss)
            pool.close()
            pool.join()
            return pd.concat(res)
        reshs = heat(resc, Chs, years, Dss, Tcs, rh_max)

        #df = join resc resh
        df = pd.merge(rescs, reshs, on=['Tc', 'Da'])
        return df
