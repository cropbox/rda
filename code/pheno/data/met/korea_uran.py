from ... import path
from ..store import Store

import numpy as np
import pandas as pd
import datetime

def read_temperature(filename):
    #FIXME: typo in pandas
    np.uin8 = np.uint8

    def parse(sheetname):
        df = ef.parse(sheetname, converters={
            'Station': int,
            'Year': int,
            'DOY': int,
        })
        df = df.rename(columns={
            'Station': 'station',
            'Year': 'year',
            'Tmax': 'tmax',
            'Tmin': 'tmin',
        })
        df = df[pd.notnull(df['DOY'])]

        def convert_jday(r, s):
            try:
                return datetime.datetime.strptime('%d-%d' % (r['year'], r[s]), '%Y-%j')
            except:
                return pd.NaT
        df['timestamp'] = df.apply(lambda r: convert_jday(r, 'DOY'), axis=1)

        df = df[['station', 'timestamp', 'tmin', 'tmax']]
        df = df.set_index(['station', 'timestamp'])
        return df

    ef = pd.ExcelFile(filename)
    df = pd.concat([parse(s) for s in ef.sheet_names])
    #HACK: remove duplicates (http://stackoverflow.com/questions/13035764/)
    df = df.groupby(level=df.index.names).last()
    return df

# hourly interpolation

import ephem
import pytz

sun = ephem.Sun()
#loc = ephem.Observer()

# Martinsburg, WV
#loc.lat = '39:27:33'
#loc.lon = '-77:58:4'

# Kearneysville, WV
#loc.lat = '39:23:17'
#loc.lon = '-77:53:8'

utc = pytz.utc
#tz = est = pytz.timezone('US/Eastern')

def sunrise(ts, tz, o):
    ts = tz.localize(ts).astimezone(utc)
    st = utc.localize(o.next_rising(sun, start=ts).datetime()).astimezone(tz)
    return st.hour + st.minute/60.

def sunset(ts, tz, o):
    ts = tz.localize(ts).astimezone(utc)
    st = utc.localize(o.next_setting(sun, start=ts).datetime()).astimezone(tz)
    return st.hour + st.minute/60.

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

def location_korea(korea_stations, station):
    s = korea_stations.loc[station]
    loc = ephem.Observer()
    loc.lat = str(s.latitude)
    loc.lon = str(s.longitude)
    loc.elevation = s.altitude
    return loc

def interpolate_korea(korea, korea_stations, station):
    tz = pytz.timezone('Asia/Seoul')
    o = location_korea(korea_stations, station)
    df = interpolate(korea.loc[station].loc['1953-05-02':], tz, o)['1953':]
    df['station'] = station
    df.set_index('station', append=True, inplace=True)
    df = df.reorder_levels(['station', 'timestamp'])
    return df

def interpolate_korea_all(korea, korea_stations):
    stations = korea.index.levels[0]
    df = pd.concat([interpolate_korea(korea, korea_stations, s) for s in stations])
    #HACK: remove duplicates for Jeju (184)
    #df = df.drop_duplicates()
    return df

def conv():
    inname = path.input.filename('raw/met/korea_uran', '8stations_weatherdata(1922-2004)', 'xls')
    korea = read_temperature(inname)

    #TODO better way to share stations file (currently from korea_jina dataset)
    #korea_stations = store.read('met', 'korea_stations')
    from . import korea_jina
    korea_stations_name = path.input.filename('raw/met/korea_jina', 'Location information', 'xlsx')
    korea_stations = korea_jina.read_stations(korea_stations_name)

    korea2 = interpolate_korea_all(korea, korea_stations)

    return Store().write(korea2, 'met', 'korea_uran')
