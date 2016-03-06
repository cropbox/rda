from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.data.path import Output

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# plot prediction with RCP projection scenarios

def predict_cherry_dc_future(cultivar, scenario, output=None):
    ds = DataSet(scenario, 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar=cultivar, stage='Peak Bloom')

    cyears = (1991, 2010)
    pyears = (2007, 2098)
    ms = ModelSuite(ds,
        calibrate_years=cyears,
        validate_years=cyears,
        export_years=pyears,
        output=output,
    )
    return ms.show_prediction(pyears, julian=True)

def plot_cherry_dc_future(df, selective=True, grouped=False, rolling=True, **kwargs):
    if rolling:
        df = pd.rolling_mean(df, window=10, min_periods=5)
    mdf = pd.melt(df.reset_index(), id_vars=['year'], var_name='model', value_name='jday')
    if selective:
        mdf = mdf[mdf.model.isin(['Obs', 'GD', 'CF', 'BF', 'DTS', 'SF', 'TP', 'SM', 'PM', 'AM', 'M', 'EN'])]
    if grouped:
        mdf['interval'] = (((mdf.year - 2000) / 20).astype(int) * 20 + 2000)
        ax = sns.boxplot(data=mdf, x='interval', y='jday', hue='model')
    else:
        ax = sns.pointplot(data=mdf, x='year', y='jday', hue='model')
    return ax

def plot_cherry_dc_future_all(output):
    cultivars = ['Yoshino', 'Kwanzan']
    scenarios = ['rcp45', 'rcp85']
    for c in cultivars:
        for s in scenarios:
            df = predict_cherry_dc_future(c, s, output)

            plt.figure(figsize=(16,10))
            plot_cherry_dc_future(df)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_grouped'.format(c, s), 'png'))

            plt.figure(figsize=(40,16))
            plot_cherry_dc_future(df, grouped=False)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_individual'.format(c, s), 'png'))

if __name__ == '__main__':
    output = Output(basepath='../output', timestamp='20160301-cherry-dc-future')
    plot_cherry_dc_future_all(output)
