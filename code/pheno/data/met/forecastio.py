from .. import path
from ..store import Store

import pandas as pd
import datetime
import pytz
import grequests

EST = pytz.timezone('US/Eastern')

META = {
    'dc': { # Washington, D.C.
        'station': 724050,
        'lat': 38.8840764,
        'lon': -77.0442509,
        'tz': EST,
    },
}

# Forecast.io API key
FORECASTIO_KEY = '6205844c8b8958f65fcf4e4c8c095539'

def fahrenheit_to_celsius(t):
    return (t - 32) * 5 / 9

def request_to_forecastio(meta, timestamp):
    params = {
        'key': FORECASTIO_KEY,
        'time': timestamp.strftime('%Y-%m-%dT%H:%M:%S')
    }
    params.update(meta)
    url = 'https://api.forecast.io/forecast/{key}/{lat},{lon},{time}'.format(**params)
    return grequests.get(url)

def parse_from_forecastio(meta, res):
    d = res.json()
    tz = pytz.timezone(d['timezone'])
    df = pd.DataFrame([{
        'timestamp': tz.localize(datetime.datetime.fromtimestamp(dd['time'])).astimezone(meta['tz']),
        'tavg': fahrenheit_to_celsius(dd['temperature']),
    } for dd in d['hourly']['data']])
    df['station'] = meta['station']
    return df.set_index(['station', 'timestamp'])

def fetch_from_forecastio(meta, timestamp):
    req = request_to_forecastio(meta, timestamp)
    res = grequests.map([req])[0]
    return parse_from_forecastio(meta, res)

def date_range(start, end):
    current = start
    while current <= end:
        yield current
        current += datetime.timedelta(days=1)

def load_from_forecastio(meta, start, end):
    reqs = [request_to_forecastio(meta, t) for t in date_range(start, end)]
    ress = [parse_from_forecastio(meta, r) for r in grequests.map(reqs)]
    return pd.concat(ress)

def conv():
    meta = META['dc']
    df0 = Store().read('met', 'usa_ds3505')
    start = df0.loc[meta['station']].index[-1].date()
    end = datetime.date(start.year, 4, 30)
    df1 = load_from_forecastio(meta, start, end)
    df = df0.combine_first(df1)
    return Store().write(df, 'met', 'usa_ds3505')
