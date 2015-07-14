from util import path

import numpy as np
import pandas as pd

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
import datetime
import pytz
from functools import reduce

####################
# Helper Functions #
####################

def date_range(start, end):
        current = start
        while current <= end:
            yield current
            current += datetime.timedelta(days=1)

def time_range(timearg):
    dates = timearg.split(':')
    for i in range(len(dates)):
        d = dates[i].lower()
        if d == 'today':
            dates[i] = datetime.datetime.today().date()
        elif d.startswith('+'):
            dates[i] = dates[i-1] + datetime.timedelta(days=int(d))
        else:
            dates[i] = datetime.datetime.strptime(d, '%Y%m%d').date()
    start = dates[0]
    end = dates[-1]
    date_range(start, end)

def fahrenheit_to_celsius(t):
    return (t - 32) * 5 / 9.

def celsius_to_fahrenheit(t):
    return t * 9 / 5. + 32

################
# NCAA Normals #
################

def load_from_noaa_normals(location_id, start, end):
    ndf = load_noaa_normals(location_id)
    dr = list(date_range(start, end))
    df = ndf.take([ndf.index.get_loc(t.replace(year=2000)) for t in dr])
    df.index = pd.DatetimeIndex(dr, name='timestamp')
    return df

def load_noaa_normals(location_id):
    url = 'ftp://ftp.ncdc.noaa.gov/pub/data/normals/1981-2010/products/station/{}.normals.txt'.format(location_id)
    res = urllib2.urlopen(url)
    lines = res.read().decode().splitlines()

    def parse_line(i):
        elem = lines[i][:16].strip()

        def elem_to_key(e):
            return {
                'dly-tmax-normal': 'tmax',
                'dly-tmin-normal': 'tmin',
            }[e]
        try:
            key = elem_to_key(elem)
        except KeyError:
            return None

        def parse_month(l, m):
            def value(s):
                return {
                    'v': s[:-1],
                    's': s[-1],
                }
            def empty(s):
                return s == '-8888'
            days = l.split()[-31:]
            return [{
                #HACK: pretend to be a leap year (2000)
                'timestamp': datetime.datetime(2000, m+1, d+1),
                key: fahrenheit_to_celsius(int(value(s)['v']) / 10.)
            } for d, s in enumerate(days) if not empty(s)]
        return sum([parse_month(lines[i+m], m) for m in range(12)], [])
    data = [parse_line(i) for i in range(len(lines))]
    dfs = [pd.DataFrame.from_records(d, index='timestamp') for d in data if d is not None]
    df = reduce(lambda x, y: x.combine_first(y), dfs)
    return df

##############
# NOAA Daily #
##############

def load_from_noaa(location_id):
    url = 'ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/daily/all/{}.dly'.format(location_id)
    res = urllib2.urlopen(url)
    lines = res.read().decode().splitlines()

    def parse_line(l):
        station = l[0:11]
        year = int(l[11:15])
        month = int(l[15:17])
        elem = l[17:21]

        def elem_to_key(e):
            return {
                'TMAX': 'tmax',
                'TMIN': 'tmin',
            }[e]
        try:
            key = elem_to_key(elem)
        except KeyError:
            return None

        def chunk(s, c):
            return [s[i:c+i] for i in range(0, len(s), c)]
        values = chunk(l[21:], 8)

        def value(s):
            return {
                'v': s[0:5],
                'm': s[5],
                'q': s[6],
                's': s[7],
            }
        def empty(s):
            return value(s)['v'] == '-9999'
        return [{
            'timestamp': datetime.datetime(year, month, i+1),
            key: int(value(s)['v']) / 10.,
        } for i, s in enumerate(values) if not empty(s)]
    data = [parse_line(l) for l in lines]
    dfs = [pd.DataFrame.from_records(d, index='timestamp') for d in data if d is not None]
    df = reduce(lambda x, y: x.combine_first(y), dfs)
    return df

#########
# Merge #
#########

def load(location_id):
    df_history = load_from_noaa(location_id)
    current = df_history.index[-1]
    start = current + datetime.timedelta(days=1)
    end = datetime.datetime(current.year, 12, 31)
    df_forecast = load_from_noaa_normals(location_id, start, end)
    df = df_history.combine_first(df_forecast)
    return df

########################
# Hourly Interpolation #
########################

import ephem
import pytz

sun = ephem.Sun()
loc = ephem.Observer()

# Martinsburg, WV
#loc.lat = '39:27:33'
#loc.lon = '-77:58:4'

# Kearneysville, WV
#loc.lat = '39:23:17'
#loc.lon = '-77:53:8'

# Washington, D.C.
loc.lat = '38:54:17'
loc.lon = '-77:00:59'

utc = pytz.utc
tz = est = pytz.timezone('US/Eastern')

def sunrise(ts, tz=tz, o=loc):
    ts = tz.localize(ts).astimezone(utc)
    st = utc.localize(o.next_rising(sun, start=ts).datetime()).astimezone(tz)
    return st.hour + st.minute/60.

def sunset(ts, tz=tz, o=loc):
    ts = tz.localize(ts).astimezone(utc)
    st = utc.localize(o.next_setting(sun, start=ts).datetime()).astimezone(tz)
    return st.hour + st.minute/60.

def interpolate(df):
    def tm(i):
        r0 = df.iloc[i]
        r1 = df.iloc[i+1]
        Tn = r0.tmin
        Tx = r0.tmax
        Tp = r1.tmin
        To = Tx - 0.39*(Tx - Tp)

        ts0 = df.index[i]
        ts1 = df.index[i+1]
        Hn = sunrise(ts0)
        Ho = sunset(ts0)
        Hx = Ho - 4
        #Hp = Hn + 24
        Hp = sunrise(ts1) + 24

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

def conv():
    location_DC = 'USW00013743'
    dc_daily = load(location_DC)

    dc_hourly = interpolate(dc_daily.loc['1945-09-30':])['1945':]
    dc_hourly['station'] = location_DC
    dc_hourly.set_index('station', append=True, inplace=True)
    dc_hourly = dc_hourly.reorder_levels(['station', 'timestamp'])

    outname = path.input.outfilename('pkl/met', 'dc', 'pkl')
    dc_hourly.to_pickle(outname)
