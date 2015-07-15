from util import path

import numpy as np
import pandas as pd
import datetime

# stations

def read_stations(filename):
    df = pd.read_excel(filename, header=1)
    df.columns = ['dummy', 'station', 'name', 'latitude', 'longitude', 'altitude']
    df = df.drop('dummy', axis=1)
    df = df.dropna()
    df = df.set_index('station')
    return df

# temperature

def read_temperature(filename):
    def parse_timestamp(v):
        return datetime.datetime.strptime(v, '%Y-%m-%d')

    df = pd.read_csv(
        filename,
        sep='|',
        header=0,
        names=['timestamp', 'station', 'tmax', 'tavg', 'tmin', 'dummy'],
        encoding='euc_kr',
    )
    df['timestamp'] = df['timestamp'].apply(parse_timestamp)
    df = df.drop('dummy', axis=1)
    df = df.set_index(['station', 'timestamp'])
    df = df.reindex_axis(['tavg', 'tmax', 'tmin'], axis=1)
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

#

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
    df = interpolate(korea.loc[station].loc['1981-01-02':], tz, o)['1981':]
    df['station'] = station
    df.set_index('station', append=True, inplace=True)
    df = df.reorder_levels(['station', 'timestamp'])
    return df

def conv():
    korea_stations_name = path.input.filename('raw/met/korea_jina', 'Location information', 'xlsx')
    korea_stations = read_stations(korea_stations_name)
    #korea_stations.to_pickle('korea_stations.pkl')

    inname = path.input.filename('raw/met/korea_jina', 'Day Max_Min_Avg Temp_ 1981-2010', 'txt')
    korea = read_temperature(inname)
    stations = korea.index.levels[0]
    korea2 = pd.concat([interpolate_korea(korea, korea_stations, s) for s in stations])

    outname = path.input.outfilename('pkl/met', 'korea_jina', 'pkl')
    korea2.to_pickle(outname)
    return korea2
