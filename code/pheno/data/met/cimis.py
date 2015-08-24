from .. import path
from ..store import Store

import numpy as np
import pandas as pd
import os
import glob
import re
import datetime

def read_station_details():
    filename = path.input.filename('raw/met/cimis', 'CIMIS Stations List (May 2015)', 'xlsx')
    return pd.read_excel(filename).set_index('Station Number')

def read_weather(filename):
    def date_parser(d, t):
        h, m = int(t[:2]), int(t[2:])
        return datetime.datetime.strptime(d, '%m/%d/%Y') + datetime.timedelta(hours=h, minutes=m)
    try:
        return pd.read_csv(filename, header=None, names=[
            'station', 'date', 'hour', 'jdate',
            'eto_qc', 'eto', 'prcp_qc', 'prcp', 'srad_qc', 'srad', 'vp_qc', 'vp',
            't_air_qc', 't_air', 'rh_qc', 'rh', 'dp_qc', 'dp',
            'ws_qc', 'ws', 'wd_qc', 'wd', 't_soil_qc', 't_soil',
        ], skipinitialspace=True, na_values=['--'], parse_dates=[[1,2]], date_parser=date_parser).rename(columns={
            'date_hour': 'timestamp',
        }).set_index(['station', 'timestamp'])
    except:
        return None

def read_weathers():
    pathname = os.path.join(path.input.basepath, 'raw/met/cimis', 'hourlyStns*/*')
    filenames = glob.glob(pathname)
    return pd.concat([read_weather(f) for f in filenames])

def _export(df, station, year, state='CA'):
    details = read_station_details()
    detail = details.loc[station]
    name = detail['Name / Location']
    header = {
        'name': name,
        'lat': detail['Latitude'],
        'lon': detail['Longitude'],
        'elev': detail['ELEV'] * 0.3048, # feet to meters
        'year': year,
    }

    basename = '{state}_{name}_{year}.wea'.format(
        state=state,
        name=re.sub(r'[ /]', '', name),
        year=year
    )
    pathname = os.path.join(path.input.basepath, 'raw/met/cimis/wea')
    os.makedirs(pathname, exist_ok=True)
    filename = os.path.join(pathname, basename)
    print(filename)
    with open(filename, 'w') as f:
        f.write("""\
station {name}
latitude {lat:.2f}
longitude {lon:.2f}
elevation {elev:.0f} m
Year {year}
Year   daytime    PAR  Tair  Rain    RH  Wind SolRad   CO2
""".format(**header))
        for k, v in df.iterrows():
            daytime = (k - datetime.datetime(year, 1, 1)).total_seconds() / (60*60*24)
            srad = np.fmax(0, v.srad) # prevent negative solar radiation
            f.write("""\
{year:4d} {daytime:9.5f} {par:6.1f} {t_air:5.1f} {rain:5.2f} {rh:5.1f} {wind:5.2f} {sol_rad:6.1f} {co2:5.1f}
""".format(
year=year,
daytime=daytime,
par=srad * 2.3,
t_air=v.t_air,
rain=v.prcp,
rh=v.rh,
wind=v.ws,
sol_rad=srad,
co2=400,
))

def export_station(weathers, station):
    df = weathers.loc[station]
    years = sorted(set(df.index.year))
    [_export(df.loc[str(y)], station, y) for y in years]

def export():
    weathers = read_weathers()
    stations = sorted(set(weathers.index.levels[0]))
    [export_station(weathers, s) for s in stations]

def conv():
    pass
