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

def extract(df, key):
    #df = df.ix[:, 0:24]
    df = df.filter(regex=key).rename(columns=lambda x: int(x.split('_')[-1]))
    df.columns.name = 'hour'
    df = df.stack(dropna=False)
    df.name = key
    df = df.reset_index()
    df.timestamp = df.apply(lambda x: x.timestamp + datetime.timedelta(hours=x.hour), axis=1)
    return df.drop(['hour'], axis=1).set_index(['station', 'timestamp'])

def interpolate(df):
    return df.unstack('station').interpolate('time').stack('station').swaplevel(0, 1).sortlevel()

def conv():
    df = pd.concat([interpolate(extract(read(n), 'tavg')) for n in NAMES])
    return Store().write(df, 'met', 'korea_shk060')
