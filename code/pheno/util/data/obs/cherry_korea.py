from util import path

import numpy as np
import pandas as pd
import datetime

def read(filename, cultivar):
    #FIXME: typo in pandas
    np.uin8 = np.uint8

    def parse(sheetname):
        df = ef.parse(sheetname, converters={
            'Station': int,
            'Year': int,
            'Bloom': int,
            'Full Bloom': int,
        })
        df = df.rename(columns={
            'Station': 'station',
            'Year': 'year',
        })
        df = df[pd.notnull(df['year'])]

        def convert_jday(r, s):
            try:
                return datetime.datetime.strptime('%d-%d' % (r['year'], r[s]), '%Y-%j')
            except:
                return pd.NaT
        def parse_stage(s):
            return df.apply(lambda r: convert_jday(r, s), axis=1)
        df['Bloom'] = parse_stage('Bloom')
        df['Full Bloom'] = parse_stage('Full Bloom')

        df['cultivar'] = cultivar
        df = df.set_index(['station', 'cultivar', 'year'])
        return df

    ef = pd.ExcelFile(filename)
    df = pd.concat([parse(s) for s in ef.sheet_names])
    return df

def conv():
    inname = path.input.filename('raw/obs/cherry_korea', '13stations_obs_PBD(1922-2004)', 'xls')
    cherry = read(inname, cultivar='Korean Cherry')

    # remove outliers
    cherry.loc[165, 'Korean Cherry', 1967]['Full Bloom'] = None

    outname = path.input.outfilename('pkl/obs', 'cherry_korea', 'pkl')
    cherry.to_pickle(outname)
