from . import base
from estimation import Estimator
from util import path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class ModelCollectionError(Exception):
    pass

class ModelCollection(object):
    def __init__(self, groups, output=None):
        self._groups = groups
        self.output = path.output if output is None else output

    def create(self):
        raise NotImplementedError

    @property
    def groups(self):
        return self._groups

    @property
    def names(self):
        return [g.dataset.name for g in self.groups]

    def export(self):
        # export results for all model groups
        [g.export() for g in self.groups]

        # export crossvalidation results
        metrics = ['rmse', 'me', 'mae', 'xe', 'ef', 'd', 'd1', 'dr']
        name = 'crossvalidation_stat'
        for how in metrics:
            self.show_crossvalidation_stat(how, ignore_estimation_error=False, name=name)
            self.show_crossvalidation_stat(how, ignore_estimation_error=True, name=name)

        # export obs vs. est plots
        self.plot_obs_vs_est('model', exclude_ensembles=False, name='obs_vs_est_by_model')
        self.plot_obs_vs_est('dataset', exclude_ensembles=True, name='obs_vs_est_by_dataset')

    def _crossvalidation_stat(self, title, df, how):
        def rank(df):
            if how == 'me':
                df = df.abs()
            ascending = not Estimator._is_higher_better(how)
            return df.rank(axis=1, ascending=not higher_is_better).mean()

        sdf = pd.DataFrame({
            'mean': df.mean(),
            'std': df.std(),
            'rank': rank(df),
        }, columns=['mean', 'std', 'rank']).transpose()
        sdf.index.name = 'type'
        sdf['title'] = title if title else self.dataset.name
        sdf['how'] = how.upper()
        sdf = sdf.reset_index().set_index(['how', 'title', 'type'])
        return sdf

    def show_crossvalidation_stat(self, how='rmse', ignore_estimation_error=False, name=None):
        titles = self.names + ['total']
        dfs = [g.show_crossvalidation(how, ignore_estimation_error) for g in self.groups]
        dfs = dfs + [pd.concat(dfs)]
        stat = pd.concat([self._crossvalidation_stat(t, d, how) for t, d in zip(titles, dfs)])

        if name:
            if ignore_estimation_error:
                basename = '{}_{}_ie'.format(name, how)
            else:
                basename = '{}_{}'.format(name, how)
            filename = self.output.outfilename('collection/results', basename, 'csv')
            stat.to_csv(filename)
        return stat

    # var = 'model' or 'dataset'
    def plot_obs_vs_est(self, var='model', exclude_ensembles=True, name=None):
        fig = plt.figure()

        def predictions(g):
            df = g.show_predictions(years=None, julian=True, exclude_ensembles=exclude_ensembles).reset_index()
            df['dataset'] = g.dataset.name
            return df
        df = pd.melt(
            pd.concat([predictions(g) for g in self.groups]),
            id_vars=['dataset', 'year', 'Obs'], var_name='model', value_name='Est'
        )
        l = np.floor(min(min(df.Obs), min(df.Est)))
        u = np.ceil(max(max(df.Obs), max(df.Est)))
        p = sns.lmplot(
            x='Obs', y='Est', col=var, data=df,
            col_wrap=5, markers='.',
            scatter_kws={
                'alpha': 0.5,
            },
        )
        [a.plot([l,u], [l,u], 'g--') for _, a in np.ndenumerate(p.axes)]

        if name:
            filename = self.output.outfilename('collection/figures', name, 'png')
            plt.savefig(filename)
        else:
            plt.show()
        plt.close(fig)
