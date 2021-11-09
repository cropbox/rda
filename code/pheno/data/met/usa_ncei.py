from .. import path
from ..store import Store

import pandas as pd
import datetime
import pytz

utc = pytz.utc
est = pytz.timezone('US/Eastern')
pst = pytz.timezone('US/Pacific')

STATIONS = {
    'dc': 724050, #13743
    'seatac': 727930, #24233
}

TIMEZONES = {
    'dc': est,
    'seatac': pst,
}

def read(name):
    df = pd.read_csv(
        path.input.filename('raw/met/ncei', name, 'csv'),
        low_memory=False
    )

    tz = TIMEZONES[name]
    def parse_timestamp(x):
        t = datetime.datetime.strptime(x, '%Y-%m-%dT%H:%M:%S')
        return utc.localize(t).astimezone(tz)
    #df['timestamp'] = df.DATE.apply(parse_timestamp)

    def parse_temp(x):
        v = x.split(',')[0]
        return None if v == '+9999' else float(v) / 10
    #df['tavg'] = df.TMP.apply(parse_temp)

    df = pd.DataFrame.from_dict({
        'timestamp': df.DATE.apply(parse_timestamp),
        'tavg': df.TMP.apply(parse_temp),
    })

    #TODO: quality control with df.QUALITY_CONTROL?
    df = df.dropna()

    df = df.sort_values(by='timestamp')
    df = df.drop_duplicates('timestamp', keep='last')
    df = df.set_index(['timestamp'])
    df = df.resample('1Min').interpolate('time').resample('1H').first()

    df['station'] = STATIONS[name]
    df = df.reset_index().set_index(['station', 'timestamp'])
    Store().write(df, 'met', f'usa_ncei_{name}')
    return df

def conv():
    df = pd.concat([read(n) for n in STATIONS])
    return Store().write(df, 'met', 'usa_ncei')
