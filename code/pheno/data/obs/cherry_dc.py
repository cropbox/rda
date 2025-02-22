from .. import path
from ..store import Store

import pandas as pd
import datetime

def read_pbd(filename, sheetname, station, stage):
    def parse_date(x, year):
        try:
            return datetime.datetime.strptime('%s-%d' % (year, x), '%Y-%j').date()
        except:
            return pd.NaT

    f = pd.ExcelFile(filename)
    df = f.parse(sheetname)
    df['station'] = station

    df = pd.melt(df, id_vars=['station', 'year'], var_name='cultivar', value_name=stage)
    df = pd.pivot_table(df, index=['station', 'cultivar', 'year'])
    df.columns.name = 'stage'

    for k, v in df.iterrows():
        #HACK: avoid float64 types?
        df.loc[k] = df.loc[k].astype(object)
        df.loc[k] = v.apply(parse_date, args=(k[2],))

    #HACK: ensure datetime objects
    for c in df:
        df[c] = pd.to_datetime(df[c])

    return df

def read_obs(filename, station, cultivar):
    def parse_date(x, year):
        try:
            return datetime.datetime.strptime(x,'%m/%d/%y').date()
        except:
            return pd.NaT

    df = pd.read_csv(filename)
    df = df.rename(columns={
        'Year': 'year',
    })
    df['station'] = station

    df = pd.melt(df, id_vars=['station', 'year'], var_name='stage')
    df['cultivar'] = cultivar

    #HACK: avoid weird type error
    df = df.set_index(['station', 'cultivar', 'year', 'stage']).unstack('stage')
    df.columns = df.columns.droplevel(0)

    for k, v in df.iterrows():
        df.loc[k] = v.apply(parse_date, args=(k[2],))

    #HACK: ensure datetime objects
    for c in df:
        df[c] = pd.to_datetime(df[c])

    return df

def conv():
    # historical PBD
    pbdname = path.input.filename('raw/obs/cherry_dc', 'Cherry_PBD', 'xls')
    pbd = read_pbd(pbdname, sheetname='DC', station='DC', stage='Peak Bloom')

    # recent observation
    obsname = path.input.filename('raw/obs/cherry_dc', 'Cherry_DC', 'csv')
    obs = read_obs(obsname, station='DC', cultivar='Yoshino')

    # merge
    #HACK: combine_first -- https://github.com/pandas-dev/pandas/issues/28481
    cherry = pbd.reindex(columns=pbd.columns|obs.columns).combine_first(obs)
    cherry = obs.reindex(columns=obs.columns|cherry.columns).combine_first(cherry)
    return Store().write(cherry, 'obs', 'cherry_dc')
