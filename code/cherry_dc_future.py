from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.data.path import Output

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.lines

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
        selected_models = ['GD', 'SF', 'BF', 'DTS', 'TP', 'CF', 'SM', 'PM', 'AM', 'M', 'EN']
        mdf = mdf[mdf.model.isin(selected_models)]
        mdf.model = pd.Categorical(mdf.model, selected_models)
        markers = ['1', '2', '3', '.', '+', 4, 5, 6, 'x', 0, '*']
    else:
        n = len(mdf['model'].unique())
        markers = list(matplotlib.lines.Line2D.markers.keys())[:n]
    if grouped:
        mdf['interval'] = (((mdf.year - 2000) / 20).astype(int) * 20 + 2000)
        ax = sns.boxplot(data=mdf, x='interval', y='jday', hue='model')
    else:
        ax = sns.pointplot(data=mdf, x='year', y='jday', hue='model', linestyles=':', markers=markers, scale=0.7, **kwargs)
        # for i, (k, g) in enumerate(mdf.groupby('model')):
        #     plt.plot(g['year'], g['jday'], linestyle=':', marker=markers[i], label=k)
        # ax = plt.legend(loc='best')
    return ax

def plot_cherry_dc_future2(df, rolling=True, **kwargs):
    if rolling:
        df = pd.rolling_mean(df, window=10, min_periods=5)
    df['F'] = df[['GD', 'SF', 'BF', 'DTS', 'TP']].mean(axis=1)
    df['C'] = df[['CF', 'SM', 'PM', 'AM']].mean(axis=1)
    mdf = pd.melt(df.reset_index(), id_vars=['year'], var_name='model', value_name='jday')
    mdf = mdf[mdf.model.isin(['F', 'C', 'EN'])]
    ax = sns.pointplot(data=mdf, x='year', y='jday', hue='model', linestyles=':', scale=0.7, **kwargs)
    return ax

def plot_cherry_dc_future_all(output):
    cultivars = ['Yoshino', 'Kwanzan']
    scenarios = ['rcp45', 'rcp85']
    for c in cultivars:
        if c == 'Yoshino':
            ylim = (40, 100)
        elif c == 'Kwanzan':
            ylim = (70, 110)
        for s in scenarios:
            df = predict_cherry_dc_future(c, s, output)

            plt.figure(figsize=(15,8))
            ax = plot_cherry_dc_future(df, grouped=True)
            ax.set_ylim(ylim)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_grouped'.format(c, s), 'png'))

            plt.figure(figsize=(15,6))
            ax = plot_cherry_dc_future(df, grouped=False)
            ax.set_ylim(ylim)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_individual'.format(c, s), 'png'))

            plt.figure(figsize=(15,6))
            ax = plot_cherry_dc_future2(df)
            ax.set_ylim(ylim)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_f_vs_c'.format(c, s), 'png'))

if __name__ == '__main__':
    output = Output(basepath='../output', timestamp='20160308-cherry-dc-future')
    plot_cherry_dc_future_all(output)
