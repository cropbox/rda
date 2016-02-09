# Multivariate Adaptive Constructed Analogs (MACA)
# http://maca.northwestknowledge.net/

from .. import path
from ..store import Store

import numpy as np
import pandas as pd
import datetime
import pytz
import ephem

###############
# Geolocation #
###############

def location(lat, lon):
    o = ephem.Observer()
    o.lat = lat
    o.lon = lon
    return o

#HACK extract lat/lon from NCDC station file
def location_from_ncdc(name):
    filename = path.input.filename('raw/met/ncdc/{}'.format(name), 'stn', 'txt')
    with open(filename) as f:
        names = f.readline().split()
        s = f.readline().split()
    #HACK override
    names = ['id', 'name', 'country', 'state', 'latitude', 'longitude', 'elevation']
    a = np.array(list(map(len, s)))
    b = a.cumsum() + np.arange(len(a))
    df = pd.read_fwf(filename, colspecs=list(zip(b-a, b)), names=names, skiprows=[0, 1])
    loc = ephem.Observer()
    loc.lat = str(df.latitude.item())
    loc.lon = str(df.longitude.item())
    return loc

############
# Timezone #
############

EST = pytz.timezone('US/Eastern')

############
# Metadata #
############

META = {
    'dc': { # Washington, D.C.
        'station': 724050,
        'loc': location('38:54:17', '-77:00:59'),
        'tz': EST,
        'c': 0.20,
    },
    # 'martinsburg': { # Martinsburg, WV
    #     'station': 724177,
    #     'loc': location('39:27:33', '-77:58:4'),
    #     'tz': EST,
    #     'c': ?,
    # },
    # 'kearneysville': { # Kearneysville, WV
    #     'station': ?,
    #     'loc': location('39:23:17', '-77:53:8'),
    #     'tz': EST,
    #     'c': ?,
    # },
}

##################
# Sunrise/sunset #
##################

sun = ephem.Sun()

def sunrise(t, o):
    srt = o.next_rising(sun, start=t).datetime()
    return (srt - t).total_seconds() / (60*60)

def sunset(t, o):
    sr = o.next_rising(sun, start=t)
    sst = o.next_setting(sun, start=sr).datetime()
    return (sst - t).total_seconds() / (60*60)

########################
# Hourly Interpolation #
########################

def transform(df, loc, c=0.39, h=4):
    Tn = df.tmin
    Tx = df.tmax
    Tp = Tn.shift(-1, '1D')
    To = Tx - c*(Tx - Tp)

    Hn = pd.Series(df.index.map(lambda t: sunrise(t, loc)), df.index)
    Ho = pd.Series(df.index.map(lambda t: sunset(t, loc)), df.index)
    Hx = Ho - h
    Hp = Hn.shift(-1, '1D') + 24

    tdf = pd.concat([Tn, To, Tx, Tp, Hn, Ho, Hx, Hp], axis=1)
    tdf.columns = ['Tn', 'To', 'Tx', 'Tp', 'Hn', 'Ho', 'Hx', 'Hp']
    return tdf

def generate(tdf):
    def T(r, t):
        Tn, To, Tx, Tp = r.Tn, r.To, r.Tx, r.Tp
        Hn, Ho, Hx, Hp = r.Hn, r.Ho, r.Hx, r.Hp

        if Hn < t <= Hx:
            #HACK: original equation looks like missing sin
            return Tn + (Tx - Tn) * np.sin((t - Hn) / (Hx - Hn) * np.pi/2)
        elif Hx < t <= Ho:
            return To + (Tx - To) * np.sin((1 + (t - Hx) / (Ho - Hx)) * np.pi/2)
        elif Ho < t <= Hp:
            return To + (Tp - To) * np.sqrt((t - Ho) / (Hp - Ho))
        else:
            return None

    def D(r):
        t0 = int(np.ceil(r.Hn))
        t1 = int(np.floor(r.Hp))
        H = range(t0, t1+1)
        return pd.Series([T(r, t) for t in H], index=H)

    hdf = tdf.apply(D, axis=1).stack()
    hdf = hdf.reset_index()
    hdf.columns = ['timestamp', 'hour', 'tavg']
    hdf['timestamp'] += hdf['hour'].map(lambda h: datetime.timedelta(hours=int(h)))
    return hdf[['timestamp', 'tavg']].set_index('timestamp')

def interpolate(df, loc, c=0.39, h=4, tz=None):
    idf = generate(transform(df, loc, c, h).dropna())
    return idf.tz_localize('UTC').tz_convert(tz)

################
# Optimization #
################

def cost(x, df, vdf, loc):
    #c, h = x
    #c, = x
    c = x
    idf = interpolate(df, loc, c=c, tz=vdf.index.tz)
    return ((idf - vdf)**2).sum().item()

# loc = NAMES['dc']['loc']
# scipy.optimize.minimize(cost, x0=(0.39,), args=(df, vdf, loc), method='nelder-mead')
# scipy.optimize.differential_evolution(cost, bounds=((0,1),), args=(df, vdf, loc), disp=True)
# scipy.optimize.brute(cost, (slice(0,1,0.01)), args=(df, vdf, loc))

#################
# File Handling #
#################

KINDS = {
    'tmax': 'tasmax',
    'tmin': 'tasmin',
}

SCENARIOS = [
    'rcp45',
    'rcp85',
]

def read(name, kind, scenario):
    df = pd.read_csv(
        path.input.filename('raw/met/maca/{}'.format(name), 'macav2livneh_{}_CCSM4_r6i1p1_{}_2006_2099_CONUS_daily_aggregated'.format(KINDS[kind], scenario), 'csv'),
        skiprows=[0,1,2,3,4,5,6,7],
        names=['timestamp', kind],
        parse_dates=[0],
    )
    if kind in ['tmax', 'tmin']:
        df[kind] -= 273.15
    return df.set_index(['timestamp'])

def read_all_kinds(name, scenario):
    return pd.concat([read(name, k, scenario) for k in KINDS], axis=1)

def load(name, scenario):
    df = read_all_kinds(name, scenario)
    m = META[name]
    idf = interpolate(df, loc=m['loc'], tz=m['tz'])
    idf['station'] = m['station']
    return idf.reset_index().set_index(['station', 'timestamp'])

def conv():
    for s in SCENARIOS:
        df = pd.concat([load(n, s) for n in META])
        Store().write(df, 'met', s)
