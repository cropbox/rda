from .. import path
from ..store import Store

import pandas as pd
import datetime
import os
import glob

def read_weather(filename):
    def date_parser(y, j, t):
        h = t.split(':')[0]
        return datetime.datetime.strptime('{}-{} {}'.format(y, j, h), '%Y-%j %H')
    df = pd.read_csv(
        filename,
        parse_dates=[['year', 'jday', 'time']],
        date_parser=date_parser
    ).rename(columns={
        'year_jday_time': 'timestamp',
    })
    df['station'] = 'UW'
    df = df.set_index(['station', 'timestamp'])
    return df.filter(['Tair']).rename(columns={
        'Tair': 'tavg',
    })

def read_weathers():
    pathname = os.path.join(path.input.basepath, 'raw/met/uw_garlic', '*WeatherData.csv')
    filenames = glob.glob(pathname)
    return pd.concat([read_weather(f) for f in filenames])

def conv():
    df = read_weathers()
    return Store().write(df, 'met', 'uw_garlic')
