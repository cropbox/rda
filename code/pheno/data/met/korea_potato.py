from .. import path
from ..store import Store

import pandas as pd

def conv():
    filename = path.input.filename('df/met', 'korea_maize', 'h5')
    df = pd.read_hdf(filename)
    df = df.loc[119].loc['2014-01-01':'2015-12-31'].reset_index()
    df['station'] = 119
    def dup(d, y):
        d = d.copy()
        d['timestamp'] = d.apply(lambda r: r.timestamp.replace(year=r.timestamp.year+y), axis=1)
        return d.set_index(['station', 'timestamp'])
    df = pd.concat([dup(df, y) for y in [0, 10, 20, 30, 40]])
    return Store().write(df, 'met', 'korea_potato')
