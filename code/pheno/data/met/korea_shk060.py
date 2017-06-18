from .. import path
from ..store import Store

import pandas as pd
import datetime

COLUMNS = [
    'station',
    'timestamp',
] + [
    'tavg_{:02d}'.format(i+1) for i in range(24)
] + [
    'td_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'hm_{:02d}'.format(i+1) for i in range(24)
] + [
    'ww_{:02d}'.format(i+1) for i in range(24)
] + [
    'wd_{:02d}'.format(i+1) for i in range(24)
] + [
    'ws_{:02d}'.format(i+1) for i in range(24)
] + [
    'si_{:02d}'.format(i+5) for i in range(16)
] + [
    'ss_{:02d}'.format(i+5) for i in range(16)
] + [
    'rn_{:02d}'.format(i+1) for i in range(24)
] + [
    'sd_hr3_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'sd_tot_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'ca_tot_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'ca_mid_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'ch_min_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'ct_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'vs_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'pv_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'pa_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'ps_{:02d}'.format(3*(i+1)) for i in range(8)
] + [
    'st_gd_{:02d}'.format(6*i+3) for i in range(4)
] + [
    'ts_{:02d}'.format(6*i+3) for i in range(4)
] + [
    'te_005_{:02d}'.format(6*i+3) for i in range(4)
] + [
    'te_01_{:02d}'.format(6*i+3) for i in range(4)
] + [
    'te_02_{:02d}'.format(6*i+3) for i in range(4)
] + [
    'te_03_{:02d}'.format(6*i+3) for i in range(4)
] + [
    '=',
]

NAMES = [
    '1973_1980',
    '1981_1990',
    '1991_2000',
    '2001_2010',
]

def read(name):
    return pd.read_csv(
        path.input.filename('raw/met/korea_shk060', name, 'txt'),
        sep='|',
        header=None,
        names=COLUMNS,
        parse_dates=['timestamp'],
        low_memory=False,
    ).set_index(['station', 'timestamp'])

def extract(df, key, dropna=False):
    #df = df.ix[:, 0:24]
    df = df.filter(regex=key).rename(columns=lambda x: int(x.split('_')[-1]))
    df.columns.name = 'hour'
    df = df.stack(dropna=False)
    df.name = key
    df = df.reset_index()
    df.timestamp = df.apply(lambda x: x.timestamp + datetime.timedelta(hours=x.hour), axis=1)
    return df.drop(['hour'], axis=1).set_index(['station', 'timestamp'])

def interval(df):
    return len(df) / df.count()

def interpolate(df):
    return df.unstack('station').interpolate('time').stack('station').swaplevel(0, 1).sortlevel()

def resample(df, na=None):
    df = df.dropna() if na is None else df.fillna(na)
    return df.unstack('station').resample('H').interpolate('time').stack('station').swaplevel(0, 1).sortlevel()

def conv():
    df = pd.concat([interpolate(extract(read(n), 'tavg')) for n in NAMES])
    return Store().write(df, 'met', 'korea_shk060')


from ..store import WeaStore

def conv_for_garlic_model():
    # year	jday	time	Tair	RH	Wind	SolRad	Rain	Tsoil
    def collect(n):
        df = read(n)
        #HACK: only choose stations in Jeju island
        df = df.loc[184:189]
        tavg = resample(extract(df, 'tavg'))
        hm = resample(extract(df, 'hm'))
        ws = resample(extract(df, 'ws'))
        si = resample(extract(df, 'si'), na=0)
        sr = si * 278 # Wh/MJ - http://web.kma.go.kr/notify/epeople/faq.jsp?bid=faq&mode=view&num=123
        rn = resample(extract(df, 'rn'))
        te_005 = resample(extract(df, 'te_005'))
        return pd.DataFrame.from_items([
            ('Tair', tavg),
            ('RH', hm),
            ('Wind', ws),
            ('SolRad', sr),
            ('Rain', rn),
            ('Tsoil', te_005),
        ]).dropna()

    def timestamp(df):
        year = df.apply(lambda x: x.name[1].year, axis=1)
        jday = df.apply(lambda x: int(x.name[1].strftime('%j')), axis=1)
        time = df.apply(lambda x: x.name[1].strftime('%H:%M'), axis=1)
        return pd.DataFrame.from_items([
            ('year', year),
            ('jday', jday),
            ('time', time),
        ])

    def export(wea):
        for station, df in wea.groupby(level=0):
            dfs = df.loc[station]
            for t, dfy in dfs.groupby(pd.TimeGrouper('A')):
                year = t.year
                WeaStore().write(dfy, f'met/garlic/{station}', year)

    def conv(n):
        df = collect(n)
        wea = pd.concat([timestamp(df), df], axis=1)
        export(wea)
    [conv(n) for n in NAMES]
