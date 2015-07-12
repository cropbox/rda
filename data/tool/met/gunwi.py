from util import path

import numpy as np
import pandas as pd
import datetime
from collections import OrderedDict
import glob

###############
# Temperature #
###############

def parse_minutely(Y, m, d, H, M):
    return datetime.datetime.strptime('{}-{}-{} {}:{}'.format(Y, m, d, H, M), '%Y-%m-%d %H:%M')

# temperature (2005)
def read_temp1(filename):
    df = pd.read_csv(filename,
                     sep='|',
                     parse_dates={'timestamp': ['Year','M ','D ','H ','M .1']},
                     date_parser=parse_minutely,
                     index_col='timestamp',
                     encoding='utf-8-sig')
    df = df.rename(columns={
        'Loc': 'station',
        'Temp': 'temp',
    }).drop(['Unnamed: 7'], axis=1)
    return df

# temperature (2006-2012)
def read_temp2(filename):
    df = pd.read_csv(filename,
                     sep='|',
                     parse_dates={'timestamp': ['연','월','일','시','분']},
                     date_parser=parse_minutely,
                     index_col='timestamp')
    df = df.rename(columns={
        '지점번호': 'station',
        '기온': 'temp',
    }).drop(['Unnamed: 7'], axis=1)
    return df

# temperature (combined)
def load_temp(dfs):
    df = pd.concat(dfs)
    g = df.groupby(['station', pd.Grouper(freq='H', label='right')])
    df = g['temp'].agg({'tavg': np.mean, 'tmin': np.min, 'tmax': np.max})
    return df

#################
# Precipitation #
#################

def parse_hourly(Y, m, d, H):
    return datetime.datetime.strptime('{}-{}-{} {}'.format(Y, m, d, H), '%Y-%m-%d %H')

def load_prcp(filename):
    df = pd.read_csv(filename,
                     sep='|',
                     parse_dates={'timestamp': ['year','M ','D ','H ']},
                     date_parser=parse_hourly,
                     index_col='timestamp',
                     encoding='utf-8-sig')
    df = df.rename(columns={
        'Loc': 'station',
        'P': 'prcp',
    }).drop(['Unnamed: 6'], axis=1)
    df = df.groupby(['station', pd.Grouper(freq='H')]).sum()
    return df

#####################
# Relative Humidity #
#####################

def load_rh(filename, station_map):
    df = pd.read_csv(filename,
                     sep='|',
                     parse_dates={'timestamp': ['Year','M ','D ','H ']},
                     date_parser=parse_hourly,
                     index_col='timestamp',
                     encoding='utf-8-sig')
    df = df.rename(columns={
        'Loc': 'station',
        'RH': 'rh',
    }).drop(['Unnamed: 6'], axis=1)
    df = df.groupby(['station', pd.Grouper(freq='H')]).mean()
    df = df.rename(index=station_map)
    return df

##########
# Export #
##########

def record(s, t, r):
    #r = r.fillna(-991)
    d = OrderedDict()
    d['year'] = t.year
    d['doy'] = t.dayofyear
    d['time'] = t.hour*100
    d['station'] = s
    d['tmax'] = r.tmax
    d['tmin'] = r.tmin
    d['tavg'] = r.tavg
    d['rh']= r.rh
    d['prcp']= r.prcp
    d['train']= -991
    d['srad'] = -991
    d['tavg_5cm'] = -991
    d['st_5cm'] = -991
    d['st_10cm'] = -991
    d['st_20cm'] = -991
    d['st_50cm'] = -991
    d['ws'] = -991
    d['wd'] = -991
    d['bp'] = -991
    d['lw_rv'] = -991
    d['lw_nm'] = -991
    d['res1'] = -991
    d['res2'] = -991
    return ','.join(str(v) for v in d.values()) + '\r\n'

def export(station, year, weather):
    outname = path.input.outfilename('pkl/met', '{}_{}'.format(station, year), 'bru')
    with open(outname, 'w') as f:
        f.writelines(record(station, t, r) for t, r in weather.loc[station][str(year)].iterrows())

def conv():
    inname = path.input.filename('raw/met/gunwi', 'Gunwi_Minute_Temperature_2005', 'txt')
    inpath = '{}/*/*'.format(path.input.path('raw/met/gunwi'))
    temp = load_temp(
        [read_temp1(inname)] +
        [read_temp2(f) for f in glob.glob(inpath)]
    )

    prcpname = path.input.filename('raw/met/gunwi', 'Gunwi_hour_Precipitation_2005_2014', 'txt')
    prcp = load_prcp(prcpname).fillna(0)

    rhname = path.input.filename('raw/met/gunwi', 'Daegu_Hour_Realtive Humidity_2005_2014', 'txt')
    rhmap = {143: 823}
    rh = load_rh(rhname, rhmap)

    # combined weather
    weather = pd.concat([temp, prcp, rh], axis=1).sort_index().dropna()

    # CIPRA (.bru)
    #[export(823, y, weather) for y in range(2005, 2012+1)]

    # pandas (.pkl)
    outname = path.input.outfilename('pkl/met', 'gunwi', 'pkl')
    weather.to_pickle(outname)
