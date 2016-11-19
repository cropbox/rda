from .. import path
from ..store import Store

import pandas as pd

def conv():
    filename = path.input.filename('raw/obs/potato_korea', 'potato_korea', 'csv')
    df = pd.read_csv(
        filename,
        parse_dates=['planting', 'emergence', 'tuber_initiation']
    ).set_index(['station', 'cultivar', 'year'])
    return Store().write(df, 'obs', 'potato_korea')
