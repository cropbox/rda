from .estimation import Estimator

import datetime
import numpy as np
import pandas as pd
import multiprocessing as mp

class DegreeDay(Estimator):
    @property
    def name(self):
        return 'DegreeDay'

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
            #'coeff0': (4.5, 250),
            #'bounds': ((0, 10), (0, 1000)),
            #'grid': (slice(3, 8, 0.1), slice(500, 1000, 5)),
            'coeff0': (1, 4.5, 250),
            'bounds': ((-100, 100), (0, 10), (0, 1000)),
            'grid': (slice(-100, 100, 1), slice(3, 8, 0.1), slice(500, 1000, 5)),
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

    def _preset(self):
        #TODO use grid and coeff_names to pick up the slice
        Tbs = np.arange(0, 10+0.1, 0.1)
        Dss = np.arange(-100, 100+1, 1)

        #tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        tdds = [pd.Series(mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        Dds = pd.concat(tdds, axis=1)
        Cds = Dds.cumsum()

        # both sides exclusive
        start_year = Cds.index.min().year + 1 + 1 #FIXME for DC cherry
        end_year = Cds.index.max().year
        years = range(start_year, end_year)

        def tabulate(year, Ds, Tbs, Rd_max=None):
            def subdata(year, Ds):
                start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Ds)
                end_date = datetime.date(year+1, 5, 31)
                df = Cds.loc[start_date:end_date]
                df = df - df.iloc[0]
                df = df.apply(np.floor)
                return df
            def populate_Rd(df, Tb, Rd_max):
                def row(sdf):
                    Rd = 0.
                    for i, v in sdf.iteritems():
                        if Rd_max and Rd >= Rd_max:
                            break
                        if v > Rd:
                            yield {'Ds': Ds, 'Tb': Tb, 'Rd': int(Rd), 'time': i}
                            Rd = v
                #return list(row(df[Tb]))
                return pd.DataFrame(row(df[Tb]))
            df = subdata(year, Ds)
            #return pd.DataFrame(sum([populate_Rd(df, Tb) for Tb in Tbs], []))
            return pd.concat([populate_Rd(df, Tb, Rd_max) for Tb in Tbs])

        tab = pd.concat([tabulate(year, Ds, Tbs) for year in years for Ds in Dss])
        return tab

    def _preset2(self):
        #TODO use grid and coeff_names to pick up the slice
        Tbs = np.arange(0, 10+0.1, 0.1)
        start_Ds = -100
        end_Ds = 100
        Dss = np.arange(start_Ds, end_Ds+1, 1)

        #tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        tdds = [pd.Series(mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        Dds = pd.concat(tdds, axis=1)
        Cds = Dds.cumsum()

        # both sides exclusive
        start_year = Cds.index.min().year + 1 + 1 #FIXME for DC cherry
        end_year = Cds.index.max().year
        years = range(start_year, end_year)

        def subdata(year):
            first_date = datetime.date(year, 1, 1)
            start_date = first_date + datetime.timedelta(days=Dss[0])
            start_date_end = first_date + datetime.timedelta(days=Dss[-1])
            end_date = datetime.date(year+1, 5, 31)
            df = Cds.loc[start_date:end_date]
            #df = df - df.iloc[0]
            #df = df.apply(np.floor)
            odf = Cds.loc[start_date:start_date_end].resample('D', how='max')
            return df, odf

        def populate_Rd(df, odf, Tb):
            def row(sdf, sodf):
                for i, v in sdf.iteritems():
                    yield [{'Ds': Ds, 'Tb': Tb, 'Rd': int(v - sodf[Dsi]), 'time': i} for Dsi, Ds in enumerate(Dss)]
            def row(sdf, sodf):
                for Dsi, Ds in enumerate(Dss):
                    Rd = 0.
                    Rd_offset = sodf[Dsi]
                    for i, v in sdf.iteritems():
                        if v > Rd:
                            yield [{'Ds': Ds, 'Tb': Tb, 'Rd': int(Rd - Rd_offset), 'time': i}]
                            Rd = v
            rows = sum(row(df[Tb], odf[Tb]), [])
            return pd.DataFrame(rows)

        def tabulate(year, Tbs):
            df, odf = subdata(year)
            #return pd.DataFrame(sum([populate_Rd(df, Tb) for Tb in Tbs], []))
            return pd.concat([populate_Rd(df, Tb) for Tb in Tbs])

        tab = pd.concat([tabulate(year, Ds, Tbs) for year in years for Ds in Dss])
        return tab

    def _preset3(self):
        #TODO use grid and coeff_names to pick up the slice
        Tbs = np.arange(0, 10+0.1, 0.1)
        Dss = np.arange(-100, 100+1, 1)

        #tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        tdds = [pd.Series(mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        Dds = pd.concat(tdds, axis=1)
        Cds = Dds.cumsum()

        # both sides exclusive
        start_year = Cds.index.min().year + 1 + 1 #FIXME for DC cherry
        end_year = Cds.index.max().year
        years = range(start_year, end_year)

        @numba.jit
        def subdata(year, Ds):
            start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Ds)
            end_date = datetime.date(year+1, 5, 31)
            df = Cds.loc[start_date:end_date]
            df = df - df.iloc[0]
            df = df.apply(np.floor)
            return df
        @numba.jit
        def populate_Rd(df, Tb, Rd_max):
            sdf = df[Tb]
            rows = []
            Rd = 0.
            for i, v in sdf.iteritems():
                if Rd_max and Rd >= Rd_max:
                    break
                if v > Rd:
                    d = {'Ds': Ds, 'Tb': Tb, 'Rd': int(Rd), 'time': i}
                    rows.append(d)
                    Rd = v
            return pd.DataFrame(rows)

        def tabulate(year, Ds, Tbs, Rd_max=None):
            df = subdata(year, Ds)
            #return pd.DataFrame(sum([populate_Rd(df, Tb) for Tb in Tbs], []))
            return pd.concat([populate_Rd(df, Tb, Rd_max) for Tb in Tbs])

        tab = pd.concat([tabulate(year, Ds, Tbs) for year in years for Ds in Dss])
        return tab

    def _preset4(self):
        #TODO use grid and coeff_names to pick up the slice
        Tbs = np.arange(0, 10+0.1, 0.1)
        Dss = np.arange(-100, 100+1, 1)

        #tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        tdds = [pd.Series(mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        Dds = pd.concat(tdds, axis=1)
        Cds = Dds.cumsum()

        # both sides exclusive
        start_year = Cds.index.min().year + 1 + 1 #FIXME for DC cherry
        end_year = Cds.index.max().year
        years = range(start_year, end_year)

        def subdata(year, Ds):
            start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Ds)
            end_date = datetime.date(year+1, 5, 31)
            df = Cds.loc[start_date:end_date]
            df = df - df.iloc[0]
            df = df.apply(np.floor)
            return df
        def populate_Rd(df, Ds, Tb, Rd_max):
            def row(sdf):
                Rd = 0.
                for i, v in sdf.iteritems():
                    if Rd_max and Rd >= Rd_max:
                        break
                    if v > Rd:
                        yield {'Ds': Ds, 'Tb': Tb, 'Rd': int(Rd), 'time': i}
                        Rd = v
            #return list(row(df[Tb]))
            return pd.DataFrame(row(df[Tb]))

        def tabulate(year, Ds, Tbs, Rd_max=None):
            df = subdata(year, Ds)
            #return pd.DataFrame(sum([populate_Rd(df, Tb) for Tb in Tbs], []))


            def multi(df, Tbs, Rd_max):
                argss = [(df, Ds, Tb, None) for Tb in Tbs]
                pool = mp.Pool()
                res = pool.map(_populate_Rd, argss)
                pool.close()
                pool.join()
                return res

            #return pd.concat([populate_Rd(df, Tb, Rd_max) for Tb in Tbs])
            return pd.concat(multi(df, Tbs, Rd_max))

        tab = pd.concat([tabulate(year, Ds, Tbs) for year in years for Ds in Dss])
        return tab

    #def _tabulate(self, Cds, year, Dss, Tbs, Rd_max=None):
    def _tabulate0(self, x):
        Cds, year, Dss, Tbs, Rd_max = x

        def tab(Cds, year, Ds, Tbs, Rd_max):
            def subdata(Cds, year, Ds):
                start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Ds)
                end_date = datetime.date(year+1, 5, 31)
                df = Cds.loc[start_date:end_date]
                df = df - df.iloc[0]
                df = df.apply(np.floor)
                return df

            def populate_Rd(df, Tb, Rd_max):
                def row(sdf):
                    Rd = 0.
                    for i, v in sdf.iteritems():
                        if Rd_max and Rd >= Rd_max:
                            break
                        if v > Rd:
                            yield {'Ds': Ds, 'Tb': Tb, 'Rd': int(Rd), 'time': i}
                            Rd = v
                #return list(row(df[Tb]))
                return pd.DataFrame(row(df[Tb]))

            df = subdata(Cds, year, Ds)
            #return pd.DataFrame(sum([populate_Rd(df, Tb) for Tb in Tbs], []))
            #return pd.concat([populate_Rd(df, Tb, Rd_max) for Tb in Tbs])
            return [populate_Rd(df, Tb, Rd_max) for Tb in Tbs]

        return pd.concat(sum([tab(Cds, year, Ds, Tbs, Rd_max) for Ds in Dss], []))

    def _preset5(self):
        #TODO use grid and coeff_names to pick up the slice
        Tbs = np.arange(0, 10+0.1, 0.1).tolist()
        Dss = np.arange(-100, 100+1, 1).tolist()
        #Tbs = np.arange(0, 10+1, 1).tolist()
        #Dss = np.arange(-10, 10+1, 1).tolist()

        tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        #tdds = [pd.Series(mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        Dds = pd.concat(tdds, axis=1)
        Cds = Dds.cumsum()


        # both sides exclusive
        start_year = Cds.index.min().year + 1 + 1 #FIXME for DC cherry
        end_year = Cds.index.max().year
        years = range(start_year, end_year)

        #tab = pd.concat([tabulate(year, Ds, Tbs) for year in years for Ds in Dss])
        #argss = [(year, Dss, Tbs, None) for year in years]
        argss = [(Cds, year, Dss, Tbs, None) for year in range(2000, 2008)]
        pool = mp.Pool()
        res = pool.map(self._tabulate, argss)
        pool.close()
        pool.join()
        tab = pd.concat(res)
        return tab

    def _preset_func(self, x):
        df, year, Dss, Tbs, Rd_max = x
        obs = self.observe(year)

        def tab(sdf, Ds, Tb):
            Rd = 0.
            for i, v in sdf.iteritems():
                if Rd_max and Rd >= Rd_max:
                    break
                if v > Rd:
                    yield {'Ds': Ds, 'Tb': Tb, 'Rd': int(Rd), 'year': year, 'est': i, 'obs': obs}
                    Rd = v
        return pd.concat([pd.DataFrame(tab(df[Tb], Ds, Tb)) for Ds in Dss for Tb in Tbs])

    def _preset6(self, years):
        #TODO use grid and coeff_names to pick up the slice
        Tbs = np.arange(0, 10+0.1, 0.1).tolist()
        Dss = np.arange(-100, 100+1, 1).tolist()
        Tbs = np.arange(0, 10+1, 1).tolist()
        Dss = np.arange(-10, 10+1, 1).tolist()

        tdds = [pd.Series(self._mets.tavg - t, name=t).clip(lower=0) / 24. for t in Tbs]
        Dds = pd.concat(tdds, axis=1)
        Cds = Dds.cumsum()

        # both sides exclusive
        start_year = Cds.index.min().year + 1 + 1 #FIXME for DC cherry
        end_year = Cds.index.max().year
        years = range(start_year, end_year)

        def subdata(Cds, year, Ds):
            start_date = datetime.date(year, 1, 1) + datetime.timedelta(days=Ds)
            end_date = datetime.date(year+1, 5, 31)
            df = Cds.loc[start_date:end_date]
            df = df - df.iloc[0]
            df = df.apply(np.floor)
            return df

        #argss = [(subdata(Cds, year, Dss[0]), Dss, Tbs, 1000) for year in years]
        argss = [(subdata(Cds, year, Dss[0]), year, Dss, Tbs, 1000) for year in range(2000, 2008)]
        pool = mp.Pool()
        res = pool.map(self._preset_func, argss)
        pool.close()
        pool.join()
        return pd.concat(res)

def _populate_Rd(x):
    return populate_Rd(*x)

def _tabulates(x):
    return tabulates(*x)

class GrowingDegreeDay(DegreeDay):
    @property
    def name(self):
        return 'GDD'

    def _calculate(self, year, met, coeff):
        T = met.tavg.resample('D', how={'tmax': np.max, 'tmin': np.min})
        tbase = coeff['Tb']
        tdd = ((T.tmax + T.tmin) / 2. - tbase).clip(lower=0)
        tdd = tdd.resample('H', fill_method='ffill') / 24.
        return tdd
