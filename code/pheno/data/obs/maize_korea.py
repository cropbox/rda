from .. import path
from ..store import Store

import pandas as pd

def read(filename):
    df = pd.read_excel(filename, skiprows=[1], na_values=['\xa0 '])
    df = df.rename(columns={
        '연도': 'year',
        '장소': 'station',
        '품종': 'cultivar',
        '파종기': 'sowing',
        '출현기': 'emergence',
        '출웅기': 'tasseling',
        '출사기': 'silking',
        '출사일수': 'silking_dates',
        '성숙기': 'maturity',
        '수확기': 'harvest',
        '기타': 'note',
    })

    if df['station'].dtype != int:
        df['station'] = df['station'].replace({
            '대구': 824, # 가산
            '수원': 119,
            '진주': 192,
            '청원': 693, # 오창
            '홍천': 522, # 화천
        })

    return df.set_index(['station', 'cultivar', 'year'])

def conv():
    filename = path.input.filename('raw/obs/maize_korea', '식용옥수수 생물계절자료', 'xlsx')
    df = read(filename)
    return Store().write(df, 'obs', 'maize_korea')
