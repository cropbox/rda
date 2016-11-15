from .. import path
from ..store import Store

import pandas as pd
import os
import glob

def read_weather(filename):
    dfd = pd.read_excel(filename, sheetname=None)
    df = pd.concat(dfd, ignore_index=True)
    df = df.rename(columns={
        '지점': 'station',
        '일시': 'timestamp',
        '기온(°C)': 'tavg',
    })
    df = df.dropna()

    if df['station'].dtype != int:
        df['station'] = df['station'].replace({
            '가산': 824, # 대구
            '진주': 192,
        })

    return df.set_index(['station', 'timestamp'])

def read_weathers():
    pathname = os.path.join(path.input.basepath, 'raw/met/korea_maize', '*.xlsx')
    filenames = glob.glob(pathname)
    return pd.concat([read_weather(f) for f in filenames])

def conv():
    df = read_weathers()
    return Store().write(df, 'met', 'korea_maize')
