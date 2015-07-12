from util import path

import pandas as pd
import datetime

def read(filename, cultivar):
    df = pd.read_csv(filename,
                     sep='|',
                     encoding='utf-8-sig')
    df = df.rename(columns={
        'LN': 'station',
        'Year': 'year',
        'FFD ': 'FFD',
    }).drop(['Unnamed: 3'], axis=1)

    def parse_date(r):
        #HACK: allegedely missing data
        if r['FFD'] == 1231:
            return None
        else:
            return datetime.datetime.strptime('%d-%04d' % (r['year'], r['FFD']), '%Y-%m%d')
    df['FFD'] = df.apply(parse_date, axis=1)
    df = df.dropna()

    df['cultivar'] = cultivar
    df = df.set_index(['station', 'cultivar', 'year'])
    return df

def load_peach(filename, cultivar):
    peach = read(filename, cultivar)

    # remove outliers
    peach.loc[165, 'Korean Peach', 1986]['FFD'] = None
    return peach

def load_pear(filename, cultivar):
    pear = read(filename, cultivar)

    # remove outliers
    pear.loc[165, 'Korean Pear', 1986]['FFD'] = None
    pear.loc[168, 'Korean Pear', 1988]['FFD'] = None
    return pear

def conv():
    def peach():
        inname = path.input.filename('raw/obs/peach_korea', 'Peach FFD', 'txt')
        df = load_peach(inname, cultivar='Korean Peach')

        outname = path.input.outfilename('pkl/obs', 'peach_korea', 'pkl')
        df.to_pickle(outname)
    peach()

    def pear():
        inname = path.input.filename('raw/obs/pear_korea', 'Pear FFD', 'txt')
        df = load_pear(inname, cultivar='Korean Pear')

        outname = path.input.outfilename('pkl/obs', 'pear_korea', 'pkl')
        df.to_pickle(outname)
    pear()
