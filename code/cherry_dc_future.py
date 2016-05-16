from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.data.path import Output

import numpy as np
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
    mdf['subject'] = 0
    ax = sns.tsplot(data=mdf, time='year', value='jday', condition='model', unit='subject', **kwargs)
    ax.set(xlabel='Year', ylabel='Predicted flowering date')
    return ax

def plot_cherry_dc_future3(df, rolling=True, **kwargs):
    if rolling:
        df = pd.rolling_mean(df, window=10, min_periods=5)
    df = df.loc[2020:]
    def agg(n, c):
        sdf = df[c]
        sdf = sdf.rename(columns={c[i]: i for i in range(len(c))})
        mdf = pd.melt(sdf.reset_index(), id_vars=['year'], var_name='subject', value_name='jday')
        mdf['Model'] = n
        return mdf
    F = ['GD', 'SF', 'BF', 'DTS', 'TP']
    C = ['CF', 'SM', 'PM', 'AM']
    mdf_FC = pd.concat([
        agg('ENf', F),
        agg('ENc', C),
    ])
    mdf_EN = pd.concat([
        agg('EN', F+C),
    ])
    #mdf = pd.concat([mdf_FC, mdf_EN])
    #ax = sns.tsplot(data=mdf, time='year', value='jday', condition='Model', unit='subject', ci=95, estimator=np.nanmean, **kwargs)
    ax = sns.tsplot(data=mdf_FC, time='year', value='jday', condition='Model', unit='subject', ci=95, color=[sns.xkcd_rgb['pale red'], sns.xkcd_rgb['denim blue']], estimator=np.nanmean, ls=':', **kwargs)
    ax = sns.tsplot(data=mdf_EN, time='year', value='jday', condition='Model', err_style=None, ci=95, color=[sns.xkcd_rgb['medium green']], estimator=np.nanmean, ax=ax, **kwargs)
    ax.set(xlabel='Year', ylabel='Predicted flowering date')
    ax.legend(loc=3, title='')
    return ax

def plot_cherry_dc_future_together(dfs, scenarios, rolling=True, ylim=None, **kwargs):
    if rolling:
        dfs = [pd.rolling_mean(df, window=10, min_periods=5) for df in dfs]
    dfs = [df.loc[2020:] for df in dfs]
    def agg(df, n, c, s):
        sdf = df[c]
        sdf = sdf.rename(columns={c[i]: i for i in range(len(c))})
        mdf = pd.melt(sdf.reset_index(), id_vars=['year'], var_name='subject', value_name='jday')
        mdf['Model'] = n
        mdf['Scenario'] = s
        return mdf
    F = ['GD', 'SF', 'BF', 'DTS', 'TP']
    C = ['CF', 'SM', 'PM', 'AM']
    def agg2(df, s):
        mdf_FC = pd.concat([
            agg(df, 'ENf', F, s),
            agg(df, 'ENc', C, s),
        ])
        mdf_EN = pd.concat([
            agg(df, 'EN', F+C, s),
        ])
        return pd.concat([mdf_FC, mdf_EN])
    mdf = pd.concat([agg2(df, s) for df, s in zip(dfs, scenarios)])
    def plot(x, y, **kwargs):
        ax = plt.gca()
        mdf = kwargs.pop('data')
        mdf_FC = mdf[mdf['Model'].isin(['ENf', 'ENc'])]
        mdf_EN = mdf[mdf['Model'] == 'EN']
        ax = sns.tsplot(data=mdf_FC, time='year', value='jday', condition='Model', unit='subject', ci=95, color={'ENf': sns.xkcd_rgb['pale red'], 'ENc': sns.xkcd_rgb['denim blue']}, estimator=np.nanmean, ls=':', ax=ax)
        ax = sns.tsplot(data=mdf_EN, time='year', value='jday', condition='Model', err_style=None, ci=95, color=[sns.xkcd_rgb['medium green']], estimator=np.nanmean, ax=ax)
    g = sns.FacetGrid(mdf, row='Scenario', legend_out=False, size=3, aspect=3)
    g.map_dataframe(plot, 'year', 'jday')
    g.set_axis_labels('Year', 'Predicted flowering date')
    g.add_legend()
    return g

def plot_cherry_dc_future_all(output):
    cultivars = ['Yoshino', 'Kwanzan']
    scenarios = ['rcp45', 'rcp85']
    for c in cultivars:
        if c == 'Yoshino':
            ylim = (50, 100)
        elif c == 'Kwanzan':
            ylim = (70, 110)

        dfs = [predict_cherry_dc_future(c, s, output) for s in scenarios]
        plot_cherry_dc_future_together(dfs, ['RCP 4.5', 'RCP 8.5'], ylim=ylim)
        plt.savefig(output.outfilename('results/{}'.format(c), '{}_rcp_f_vs_c'.format(c), 'png'), dpi=300)
        #continue

        for s in scenarios:
            df = predict_cherry_dc_future(c, s, output)

            plt.figure(figsize=(12,5))
            ax = plot_cherry_dc_future(df, grouped=True)
            ax.set_ylim(ylim)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_grouped'.format(c, s), 'png'), dpi=300)

            plt.figure(figsize=(12,5))
            ax = plot_cherry_dc_future(df, grouped=False)
            ax.set_ylim(ylim)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_individual'.format(c, s), 'png'), dpi=300)

            plt.figure(figsize=(12,5))
            ax = plot_cherry_dc_future2(df)
            ax.set_ylim(ylim)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_f_vs_c_legacy'.format(c, s), 'png'), dpi=300)

            plt.figure(figsize=(12,5))
            ax = plot_cherry_dc_future3(df)
            ax.set_ylim(ylim)
            plt.savefig(output.outfilename('results/{}'.format(c), '{}_{}_f_vs_c'.format(c, s), 'png'), dpi=300)

if __name__ == '__main__':
    output = Output(basepath='../output', timestamp='20160308-cherry-dc-future')
    plot_cherry_dc_future_all(output)
