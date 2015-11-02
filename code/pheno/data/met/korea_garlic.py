from .. import path
from ..store import Store

import numpy as np
import pandas as pd
import datetime
import pytz
import ephem
from geopy.geocoders import GoogleV3

# weather

def read(filename):
    def parse(xls, s):
        df = xls.parse(s, header=1).reset_index().rename(columns={
            'index': 'timestamp',
            'MaxT': 'tmax',
            'MinT': 'tmin',
            'AveT': 'tavg',
        })
        df['station'] = xls.parse(s).columns[0]
        return df.set_index(['station', 'timestamp'])
    with pd.ExcelFile(filename) as xls:
        df = pd.concat([parse(xls, s) for s in xls.sheet_names])
    return df
    # return df.filter(['Tair']).rename(columns={
    #     'Tair': 'tavg',
    # })

# location from geocoding

def location(station):
    g = GoogleV3().geocode('{}, Korea'.format(station))
    loc = ephem.Observer()
    loc.lat = str(g.latitude)
    loc.lon = str(g.longitude)
    loc.elevation = g.altitude
    return loc

# hourly interpolation

def sunrise(ts, tz, o):
    sun = ephem.Sun()
    utc = pytz.utc
    ts = tz.localize(ts).astimezone(utc)
    st = utc.localize(o.next_rising(sun, start=ts).datetime()).astimezone(tz)
    return st.hour + st.minute/60

def sunset(ts, tz, o):
    sun = ephem.Sun()
    utc = pytz.utc
    ts = tz.localize(ts).astimezone(utc)
    st = utc.localize(o.next_setting(sun, start=ts).datetime()).astimezone(tz)
    return st.hour + st.minute/60

def interpolate(df, tz, o):
    def tm(i):
        r0 = df.iloc[i]
        r1 = df.iloc[i+1]
        Tn = r0.tmin
        Tx = r0.tmax
        Tp = r1.tmin
        To = Tx - 0.39*(Tx - Tp)

        ts0 = df.index[i]
        ts1 = df.index[i+1]
        Hn = sunrise(ts0, tz, o)
        Ho = sunset(ts0, tz, o)
        Hx = Ho - 4
        #Hp = Hn + 24
        Hp = sunrise(ts1, tz, o) + 24

        a = Tx - Tn
        R = Tx - To
        b = (Tp - To) / (Hp - Ho)**0.5

        def T(t):
            if Hn < t <= Hx:
                return Tn + a * (t - Hn) / (Hx - Hn) * np.pi/2
            elif Hx < t <= Ho:
                return To + R * np.sin(np.pi/2 + (t - Hx)/4. * np.pi/2)
            elif Ho < t <= Hp:
                return To + b * (t - Ho)**0.5

        t0 = int(np.ceil(Hn))
        t1 = int(np.floor(Hp))
        tavg = [T(t) for t in range(t0, t1+1)]
        index = pd.date_range(ts0 + datetime.timedelta(hours=t0), periods=len(tavg), freq='H', name='timestamp')
        return pd.DataFrame(data={'tavg': tavg}, index=index).dropna()
    return pd.concat([tm(i) for i in range(len(df)-1)])

def hourly(weather, station):
    tz = pytz.timezone('Asia/Seoul')
    o = location(station)
    df = interpolate(weather.loc[station], tz, o)
    df['station'] = station
    df.set_index('station', append=True, inplace=True)
    df = df.reorder_levels(['station', 'timestamp'])
    return df

def conv():
    filename = path.input.filename('raw/met/korea_garlic', 'Garlic_climatic data_Korea', 'xlsx')
    df = read(filename)
    stations = df.index.levels[0]
    weather = pd.concat([hourly(df, s) for s in stations])
    return Store().write(weather, 'met', 'korea_garlic')
