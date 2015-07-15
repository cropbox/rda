from ... import path

import numpy as np
import pandas as pd
import datetime

def read(filename, station):
    def parse_date(x, year):
        try:
            return datetime.datetime.strptime('%s-%s' % (year, x.strip()), '%Y-%m/%d')
        except:
            return None

    def extract_year(r):
        a = np.array([x.year for x in r])
        try:
            return a[~np.isnan(a)][0]
        except:
            return None

    def parse(s):
        df = f.parse(sheetname=s, skiprows=[0, 1])
        df = df.rename(columns={
            'No.- Variety': 'cultivar',
            'FB': 'Full Bloom',
            'PF ': 'Petal Fall',
            'Harvest data not taken': 'Harvest',
        })

        df['station'] = station
        df['cultivar'] = df['cultivar'].apply(lambda s: ''.join(s.split()[1:]))
        df = df[['station', 'cultivar', 'Full Bloom', 'Petal Fall', 'Harvest']]
        df = df.set_index(['station', 'cultivar'])

        for k, v in df.iteritems():
            df[k] = v.apply(parse_date, args=(s,))
        df = df.dropna(how='all')

        #df['year'] = df.apply(extract_year, axis=1)
        df['year'] = int(s)
        df = df.set_index(['year'], append=True)
        return df

    f = pd.ExcelFile(filename)
    return pd.concat([parse(s) for s in f.sheet_names]).sort()

def conv():
    inname = path.input.filename('raw/obs/apple_kearneysville', 'Apple Tree Phenology1997-2007', 'xlsx')
    observation = read(inname, station='Kearneysville')

    outname = path.input.outfilename('pkl/obs', 'apple_kearneysville', 'pkl')
    observation.to_pickle(outname)
