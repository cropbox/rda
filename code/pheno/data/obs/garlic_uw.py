from .. import path
from ..store import Store

import pandas as pd

def read(filename):
    df = pd.read_excel(filename, na_values=['-'])
    df = df.rename(columns={
        'Year': 'year',
        'Cultivar': 'cultivar',
    })

    # Use first year
    df['year'] = df['year'].apply(lambda x: int(x.split('-')[0]))

    # Remove 'Date' suffix from column names
    df.columns = [s.replace('Date', '').strip() for s in df.columns]

    # Set default station name
    df['station'] = 'UW'

    return df.set_index(['station', 'cultivar', 'year'])

def conv():
    filename = path.input.filename('raw/obs/garlic_uw', 'GarlicPhenology', 'xlsx')
    df = read(filename)
    return Store().write(df, 'obs', 'garlic_uw')
