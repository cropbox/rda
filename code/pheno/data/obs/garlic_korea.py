from .. import path
from ..store import Store

import pandas as pd

def read(filename):
    def parse(xls, sheetname):
        df = xls.parse(sheetname).rename(index={
            'Sinan': 'Shinan',
            'Jeoje': 'Geoje',
            'Changnyeung': 'Changnyeong',
        })
        df['cultivar'] = 'Korean Garlic'
        ss = df.set_index('cultivar', append=True).stack()
        ss.index.names = ['station', 'cultivar', 'year']
        return ss
    with pd.ExcelFile(filename) as xls:
        names = ['seeding', 'emergence']
        df = pd.concat([parse(xls, s) for s in names], axis=1)
        df.columns = names
    return df

def conv():
    #filename = path.input.filename('raw/obs/garlic_korea', 'Garlic_biological data_Korea', 'xlsx')
    filename = path.input.filename('raw/obs/garlic_korea', 'Garlic_biological data_Korea2', 'xlsx')
    df = read(filename)
    return Store().write(df, 'obs', 'garlic_korea')
