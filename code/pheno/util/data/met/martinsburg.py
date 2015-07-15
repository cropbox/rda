from ... import path

import numpy as np
import pandas as pd
import datetime
import re

# temperature & precipitation

def read(filename, station):
    def parse_yearmoda(v):
        return datetime.datetime.strptime(str(v), '%Y%m%d')

    def parse_farhenheit(v):
        #v = float(v.replace('*', '')) if type(v) in [str, unicode] else v
        v = float(v.replace('*', '')) if type(v) not in [int, float] else v
        if v == 9999.9:
            return np.nan
        else:
            return (v - 32)*(5/9.)

    def parse_prcp(v):
        #v = float(re.sub(r'[a-zA-Z]', '', v)) if type(v) in [str, unicode] else v
        v = float(re.sub(r'[a-zA-Z]', '', v)) if type(v) not in [int, float] else v
        return v if v != 99.99 else np.nan

    df = pd.read_excel(filename, converters={
        'YEARMODA': parse_yearmoda,
        'TEMP': parse_farhenheit,
        'MAX': parse_farhenheit,
        'MIN': parse_farhenheit,
        'PRCP': parse_prcp,
    })

    df = df[['YEARMODA', 'TEMP', 'MAX', 'MIN', 'PRCP']].rename(columns={
        'YEARMODA': 'timestamp',
        'TEMP': 'tavg',
        'MAX': 'tmax',
        'MIN': 'tmin',
        'PRCP': 'prcp',
    })

    df['station'] = 'Martinsburg'
    df = df.set_index(['station', 'timestamp'])
    return df

# hourly interpolation

import ephem
import pytz

sun = ephem.Sun()
loc = ephem.Observer()

# Martinsburg, WV
loc.lat = '39:27:33'
loc.lon = '-77:58:4'

# Kearneysville, WV
#loc.lat = '39:23:17'
#loc.lon = '-77:53:8'

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
    inname = path.input.filename('raw/met/martinsburg', 'Martinsburg weather data 1949-2010 data', 'xlsx')
    martinsburg = read(inname, station='Martinsburg')

    martinsburg2 = interpolate(martinsburg.loc['Martinsburg'].loc['1949-09-30':])['1949':]
    martinsburg2['station'] = 'Martinsburg'
    martinsburg2.set_index('station', append=True, inplace=True)
    martinsburg2 = martinsburg2.reorder_levels(['station', 'timestamp'])

    outname = path.input.outfilename('pkl/met', 'martinsburg', 'pkl')
    martinsburg2.to_pickle(outname)
    return martinsburg2
