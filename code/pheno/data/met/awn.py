from .. import path
from ..store import Store

import numpy as np
import pandas as pd
import datetime
import calendar
import os
import glob
import re
from robobrowser import RoboBrowser
from urllib.parse import urlencode
from io import StringIO

# CAUTION: default station must be set to the last item (e.g. Woodburn South)

input = path.Input(basepath='../input/raw/met/awn')

# HACK more restricted set
import string
VALID_CHARS = frozenset("-()%s%s" % (string.ascii_letters, string.digits))
def _slugify(v):
    return ''.join(c for c in str(v) if c in VALID_CHARS)

class Date:
    REQUEST_FORMAT = '%b %d, %Y'
    STATION_FORMAT = '%B %d, %Y'

    def __init__(self, year=1989, month=1, day=1):
        self.set(year, month, day)

    def set(self, year, month, day):
        self.t = datetime.date(year, month, day)
        return self

    def set_as_format(self, datestr, fmt=None):
        if fmt is None:
            fmt = Date.REQUEST_FORMAT
        self.t = datetime.datetime.strptime(datestr, fmt).date()
        return self

    @property
    def start(self):
        return self.t.strftime(self.REQUEST_FORMAT)

    @property
    def last_day(self):
        return calendar.monthrange(self.t.year, self.t.month)[1]

    @property
    def end(self):
        return self.t.replace(day=self.last_day).strftime(self.REQUEST_FORMAT)

    def advance(self):
        self.t = (self.t + datetime.timedelta(days=31)).replace(day=1)
        return self

    def over(self, date=None):
        if date is None:
            date = datetime.date.today()
        return self.t < date

    def __str__(self):
        return self.t.__str__()


class Scraper:
    DATA_URL = 'http://weather.wsu.edu/awn.php?page=hourlydata'
    STATION_URL = 'http://weather.wsu.edu/awn.php?page=station_details'
    MAP_URL = 'http://weather.wsu.edu/gmap/GMapSelectSession.php'

    def __init__(self):
        self.b = RoboBrowser(parser='lxml')

    def login(self):
        self.b.open(self.DATA_URL)
        f = self.b.get_form()
        f['user'] = 'tomyun'
        f['pass'] = 'nuymot'
        self.b.submit_form(f)
        l = self.b.select('a[href^="awn.php?page=hourlydata"]')
        self.b.follow_link(l[0])
        self._fetch_stations()
        return self

    def _fetch_stations(self):
        rs = self.b.find_all('option', title='Public Station')
        self.stations = {int(t['value']): t.text for t in rs}
        self.stations_by_name = {v: k for k, v in self.stations.items()}

    def _fetch_station_detail(self, station):
        self.b.open('{}&UNIT_ID={}'.format(self.STATION_URL, station))
        m = re.search('latitude (?P<lat>-?\d+\.?\d*)&deg, longitude (?P<lon>-?\d+\.?\d*)°, elevation (?P<elev>\d+) .+ installed on (?P<date>\D+ \d+, \d+)', self.b.parsed.text)
        return {
            'lat': float(m.group('lat')),
            'lon': float(m.group('lon')),
            'elev': float(m.group('elev')) * 0.3048, # feet to meters
            'date': Date().set_as_format(m.group('date'), Date.STATION_FORMAT)
        }

    def select_station(self, station):
        def toggle(station):
            qs = urlencode({
                '_': datetime.datetime.now().timestamp(),
                'idvalue': station,
                'startdate': '',
                'enddate': '',
                'id': 'undefined',
            })
            self.b.open('{}?{}'.format(self.MAP_URL, qs))
        self.b.open(self.MAP_URL)
        ts = self.b.find_all('a')
        selected = set([int(re.search('value=(\d+)', t.attrs['onclick']).group(1)) for t in ts])
        if not station in selected:
            toggle(station)
        [toggle(s) for s in selected - {station}]
        return self

    def _request_one_period(self, date):
        self.b.open(self.DATA_URL)
        f = self.b.get_form()
        f['startDate3'] = date.start
        f['endDate3'] = date.end
        f['unit'] = 'Metric'
        f['dateChanged'] = 1
        self.b.submit_form(f)

    def _update_actual_start_date(self, date):
        try:
            text = self.b.select('#tabrow1-1 font')[0].text
            m = re.search('(installed on|date is) (?P<date>\D+ \d+, \d+)', text)
            return date.set_as_format(m.group('date'))
        except:
            return None

    def _parse(self):
        # download CSV
        f = self.b.get_forms()[1]
        self.b.submit_form(f)
        text = self.b.parsed.text.split('\n\n')[0]
        sio = StringIO(text)
        def date_parser(d, t):
            return datetime.datetime.strptime(d, '%B %d, %Y') + datetime.timedelta(hours=int(t[:2])-1)
        return pd.read_csv(sio, skiprows=2, skipinitialspace=True, parse_dates=[[1,2]], date_parser=date_parser).rename(columns={
            'Date_Hour PDT': 'timestamp',
            'UNIT_ID': 'station',
        }).set_index(['station', 'timestamp'])

    def request(self, station):
        self.select_station(station)
        date = self._fetch_station_detail(station)['date']
        dfs = []
        while date.over():
            print(date)
            self._request_one_period(date)
            if self._update_actual_start_date(date):
                continue
            dfs.append(self._parse())
            date.advance()
        return pd.concat(dfs)

    def _export(self, df, station, year, state):
        name = self.stations[station]
        header = self._fetch_station_detail(station)
        header.update({
            'name': name,
            'year': year,
        })
        sdf = df.loc[station].loc[str(year)]

        basefilename = '{state}_{name}_{year}.wea'.format(
            state=state,
            name=_slugify(name),
            year=year
        )
        pathname = os.path.join(input.basepath, 'wea')
        os.makedirs(pathname, exist_ok=True)
        filename = os.path.join(pathname, basefilename)
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
            for k, v in sdf.iterrows():
                def extract(key):
                    try:
                        return v[key]
                    except:
                        return np.nan
                def format(val, digits=1, precision=0):
                    if np.isnan(val):
                        return '{0:>{1}}'.format('-99', digits)
                    else:
                        return '{0:{1}.{2}f}'.format(val, digits, precision)
                daytime = (k - datetime.datetime(year, 1, 1)).total_seconds() / (60*60*24) + 1
                sol_rad = extract('Solar Rad W/m²')
                par = 2.3 * sol_rad
                t_air = extract('Avg Air Temp °C')
                rain = extract('Tot Prec mm')
                rh = extract('Rel Hum %')
                wind = extract('Speed m/s')
                co2 = 400
                f.write("""\
{year:4d} {daytime:9.5f} {par} {t_air} {rain} {rh} {wind} {sol_rad} {co2}
""".format(
    year=year,
    daytime=daytime,
    par=format(par, 6, 1),
    t_air=format(t_air, 5, 1),
    rain=format(rain, 5, 2),
    rh=format(rh, 5, 1),
    wind=format(wind, 5, 2),
    sol_rad=format(sol_rad, 6, 1),
    co2=format(co2, 5, 1),
))

    def export_station(self, station):
        df = self.request(station)
        #station = df.index.levels[0].item()

        # save original dataset for each station in HDF5 format
        state = 'WA'
        name = self.stations[station]
        Store(input).write(df, '', '{}_{}'.format(state, name))

        # export yearly dataset for each station in MAIZSIM .wea format
        years = sorted(set(df.index.levels[1].year))
        [self._export(df, station, y, state) for y in years]

    def export(self):
        [self.export_station(s) for s in self.stations]


class Summary:
    def __init__(self, name='awn'):
        self.pathname = os.path.join(path.input.basepath, 'raw/met/{}/wea'.format(name))

    def export(self, filename='station_summary.txt'):
        weas = glob.glob(os.path.join(self.pathname, '*.wea'))
        with open(os.path.join(self.pathname, filename), 'w') as f:
            f.write("State\tCity\tStation\tLatitude\tLongitude\tElevation\tYear\tGSMT\tfilename\tNote\n")
            [f.write(self.summary(w)) for w in weas]

    def summary(self, filename):
        print(filename)

        basename = os.path.splitext(os.path.basename(filename))[0]
        state = re.match(r'([a-zA-Z0-9]+)_', basename).group(1)
        with open(filename) as f:
            def extract(key, pattern):
                return re.match(r'{} ({})'.format(key, pattern), f.readline()).group(1)
            station = extract('station', r'.+')
            lat = float(extract('latitude', r'-?\d+\.\d*'))
            lon = float(extract('longitude', r'-?\d+\.\d*'))
            elev = int(extract('elevation', r'-?\d+'))
            year = int(extract('Year', r'\d+'))

        df = pd.read_csv(filename, skiprows=5, delim_whitespace=True)
        def daytime_parser(d):
            return datetime.datetime(year, 1, 1) + datetime.timedelta(days=d-1)
        def calc_growing_season_mean_temperature():
            ts = df['daytime'].apply(daytime_parser)
            try:
                sd = ts.iloc[0].date()
                ed = ts.iloc[-1].date()
            except:
                return '-99'
            gsd = datetime.date(year, 4, 1)
            ged = datetime.date(year, 9, 30)
            if sd > gsd or ed < ged:
                return '-99'
            t = df[ts.dt.month.isin(range(4, 9+1))].Tair.mean()
            if np.isnan(t):
                return '-99'
            else:
                return '{:.2f}'.format(t)
        gsmt = calc_growing_season_mean_temperature()
        note = 'None'
        return "{state}\t{city}\t{station}\t{lat:.2f}\t{lon:.2f}\t{elev:.0f}\t{year}\t{gsmt}\t{basename}\t{note}\n".format(
            state=state,
            city=station,
            station=station,
            lat=lat,
            lon=lon,
            elev=elev,
            year=year,
            gsmt=gsmt,
            basename=basename,
            note=note
        )


class JulianDateFixer:
    def __init__(self):
        self.pathname = os.path.join(path.input.basepath, 'raw/met/awn/wea')

    def fix(self):
        weas = glob.glob(os.path.join(self.pathname, '*.wea'))
        [self._fix(w) for w in weas]

    def _fix(self, filename):
        s = ''
        with open(filename) as f:
            for _ in range(6):
                s += f.readline()
            for l in f:
                v = l.split()
                v[1] = '{:.5f}'.format(float(v[1]) + 1)
                s += '{:>4} {:>9} {:>6} {:>5} {:>5} {:>5} {:>5} {:>6} {:>5}\n'.format(*v)
        with open(filename, 'w') as f:
            f.write(s)


# for MAIZSIM
#HACK resource limitaiton when using only one instance
def export_with_one_instance():
    s = Scraper()
    s.login()
    s.export()

def export():
    stations = Scraper().login().stations
    #FIXME remove slice
    # last (21) should be Touchet
    #stations = list(stations)[22:]
    # last (80) should be Grandview NE
    #stations = list(stations)[81:]
    # last (144) should be Carlson
    #stations = list(stations)[145:]
    [Scraper().login().export_station(s) for s in stations]

def conv():
    pass
