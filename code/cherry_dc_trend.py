from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.model.base import DEFAULT_ESTIMATORS
from pheno.data.path import Output

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import multiprocessing as mp

# trend analysis with varying window

def create_cherry_dc():
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(stage='Peak Bloom')
    return ModelGroup(ds,
        calibrate_years=(1990, 2010), # close to (1991, 2010) from Chung et al. (2011)
        validate_years=[(1946, 1989), (2011, 2014)],
        export_years=(1937, 2015),
    )

def _func_cherry_dc_trend(x):
    y, ds, output = x
    return ModelGroup(ds,
        calibrate_years=(y, y+15),
        validate_years=(y+16, y+19),
        export_years=(y, y+19),
        output=output,
    )#.export()

def _func_cherry_dc_trend2(x):
    y, ds, output = x
    return ModelSuite(ds,
        calibrate_years=(y, y+15),
        validate_years=(y+16, y+19),
        export_years=(y, y+19),
        output=output,
    )

def create_cherry_dc_trend():
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(stage='Peak Bloom')
    output = Output(basepath='../output', timestamp='20160127-cherry-dc-trend')
    years = range(1946, 1999+1)
    #years = reversed(range(1946, 1999+1))
    with mp.Pool() as p:
        return p.map(_func_cherry_dc_trend, [(y, ds, output) for y in years])
        #return dict(zip(years, p.map(_func_cherry_dc_trend, [(y, ds, output) for y in years])))

def predict_cherry_dc_trend(cultivar):
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar=cultivar, stage='Peak Bloom')
    output = Output(basepath='../output', timestamp='20160127-cherry-dc-trend')
    years = range(1946, 1999+1)

    def dataframe(y):
        ms = ModelSuite(ds,
            calibrate_years=(y, y+15),
            validate_years=(y+16, y+19),
            export_years=(y, y+19),
            output=output,
        )
        df = ms.show_prediction((1946, 2014), julian=True)
        df = df.reset_index()
        df['base'] = y
        return df.set_index(['base', 'year'])
    return pd.concat([dataframe(y) for y in years])

def predict_cherry_dc_future(cultivar, scenario):
    ds = DataSet(scenario, 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar=cultivar, stage='Peak Bloom')
    output = Output(basepath='../output', timestamp='20160209-cherry-dc-future')
    cyears = (1990, 2010)
    pyears = (2007, 2098)
    ms = ModelSuite(ds,
        calibrate_years=cyears,
        validate_years=cyears,
        export_years=pyears,
        output=output,
    )
    return ms.show_prediction(pyears, julian=True)

def plot_cherry_dc_future(df, selective=True, grouped=True):
    mdf = pd.melt(df.reset_index(), id_vars=['year'], var_name='model', value_name='jday')
    if selective:
        mdf = mdf[mdf.model.isin(['Obs', 'GD', 'CF', 'BF', 'DTS', 'SF', 'TP', 'SM', 'PM', 'AM', 'M', 'EN'])]
    if grouped:
        mdf['interval'] = (((mdf.year - 2000) / 20).astype(int) * 20 + 2000)
        ax = sns.boxplot(data=mdf, x='interval', y='jday', hue='model')
    else:
        ax = sns.pointplot(data=mdf, x='year', y='jday', hue='model')
    return ax

def plot_cherry_dc_future_all():
    cultivars = ['Yoshino', 'Kwanzan']
    scenarios = ['rcp45', 'rcp85']
    for c in cultivars:
        for s in scenarios:
            df = predict_cherry_dc_future(c, s)

            plt.figure(figsize=(16,10))
            plot_cherry_dc_future(df)
            plt.savefig('{0}/{0}_{1}_grouped.png'.format(c, s))

            plt.figure(figsize=(40,16))
            plot_cherry_dc_future(df, grouped=False)
            plt.savefig('{0}/{0}_{1}_individual.png'.format(c, s))

# ds.observation().apply(lambda x: int(x.strftime('%j'))).mean()
# ds.observation().apply(lambda x: int(x.strftime('%j'))).std()
# df.mean()
# df.std()

def metric_cherry_dc_trend(cultivar, max_counts=20):
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar=cultivar, stage='Peak Bloom')
    output = Output(basepath='../output', timestamp='20160127-cherry-dc-trend')
    years = range(1946, 1999+1)
    # years = range(1946, 1999+1, 3)
    # years = range(1947, 1999+1, 3)
    # years = range(1948, 1999+1, 3)

    def dataframe(y):
        ms = ModelSuite(ds,
            calibrate_years=(y, y+15),
            validate_years=(y+16, y+19),
            export_years=(y, y+19),
            output=output,
        )
        counts = min(max_counts, max(0, 2014 - (y+16) + 1))
        if counts == 0:
            return None
        def metric(y, i):
            df = ms.show_metric((y+16, y+16+i))
            df = df.reset_index()
            df['base'] = y
            df['count'] = i+1
            return df.set_index(['base', 'model', 'count'])
        df = pd.concat([metric(y, i) for i in range(counts)])
        df.to_csv('{}/{}.csv'.format(cultivar, y))
        return df
    df = pd.concat([dataframe(y) for y in years])
    df.to_csv('{}/{}.csv'.format(cultivar, cultivar))
    return df

def plot_cherry_dc_trend(df):
    #df = pd.read_csv('Yoshino.csv', na_values=['--'])
    #sns.boxplot(x='count', y='D', hue='model', data=df)
    metrics = df.columns[3:]
    for m in metrics:
        g = sns.FacetGrid(df, col='model', col_wrap=6)
        g.map(sns.boxplot, 'count', m)
        plt.savefig('{}.png'.format(m))

# crossvalidation with varying size of dataset

def create_cherry_dc_list(output=None):
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(stage='Peak Bloom')
    return [
        ModelGroup(ds,
            calibrate_years=(1991, 2010),
            validate_years=[(1946, 1969), (1974, 1990), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        ),
        ModelGroup(ds,
            calibrate_years=(1974, 2010),
            validate_years=[(1946, 1969), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        ),
        ModelGroup(ds,
            calibrate_years=[(1951, 1969), (1974, 2010)],
            validate_years=[(1946, 1950), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        ),
    ]

if __name__ == '__main__':
    output = Output(basepath='../output', timestamp='20160221-cherry-dc-long')
    groups = create_cherry_dc_list(output)
    collections = [ModelCollection(g) for g in groups]
    [c.export() for c in collections]
