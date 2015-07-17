from .. import path
from ..store import Store

import pandas as pd
import datetime

NAMES = [
    'dc', #724050
    'martinsburg', #724177
]

def read(name):
    df = pd.read_csv(
        path.input.filename('raw/met/ncdc/{}'.format(name), 'dat', 'txt'),
        skiprows=[0],
        low_memory=False
    )

    names = df.columns[0].split() + ['dummy']
    df = df.reset_index()
    df.columns = names

    station = df.USAF.unique().item()

    #TODO: quality control with df.Q?
    #[0, 1, 4, 5, 9, A, C, I, M, P, R, U]

    df['timestamp'] = df.apply(lambda x: datetime.datetime.strptime('{:08d}{:04d}'.format(x.Date, x.HrMn), '%Y%m%d%H%M'), axis=1)
    df = df.drop([
        'USAF', 'NCDC',
        'Date', 'HrMn',
        'I', 'Type', 'QCP', 'Q',
        'dummy'
    ], axis=1).rename(columns={'Temp': 'tavg'})
    df = df.set_index(['timestamp'])
    df = df.resample('1Min').interpolate('time').resample('1H', how='first')

    df['station'] = station
    return df.reset_index().set_index(['station', 'timestamp'])

def conv():
    df = pd.concat([read(n) for n in NAMES])
    return Store().write(df, 'met', 'usa_ds3505')
