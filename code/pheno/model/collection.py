from ..estimation.base import Estimator
from ..data import path

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
        # export sensitivity analysis results
        self.show_sensitivity(deltas=list(range(-5, 5+1)), name='sensitivity')

        # export crossvalidation results
        self.show_crossvalidation_all(ignore_estimation_error=True, name='crossvalidation')

        # export obs vs. est plots
        self.plot_obs_vs_est('model', exclude_ensembles=False, name='obs_vs_est_by_model')
        self.plot_obs_vs_est('dataset', exclude_ensembles=True, name='obs_vs_est_by_dataset')

        # export results for all model groups
        [g.export() for g in self.groups]

    def _rank(self, df, how, dropna=True):
        if dropna:
            #HACK remove NaN before converting integer ranks
            df = df.dropna()
        if how == 'me':
            df = df.abs()
        ascending = not Estimator._is_higher_better(how)
        return df.rank(axis=1, ascending=ascending)

    def _crossvalidation_raw(self, title, df, how):
        #HACK keep the original index
        df = df.copy()
        df.index = range(len(df))
        df.index.name = 'seq'

        sdf = df
        sdf['title'] = title if title else self.dataset.name
        sdf['how'] = how.upper()
        sdf = sdf.reset_index().set_index(['how', 'title', 'seq'])
        return sdf

    def _crossvalidation_rank(self, title, df, how):
        #HACK keep the original index
        df = df.copy()
        df.index = range(len(df))
        df.index.name = 'seq'

        sdf = self._rank(df, how)
        sdf['title'] = title if title else self.dataset.name
        sdf['how'] = how.upper()
        sdf = sdf.reset_index().set_index(['how', 'title', 'seq'])
        return sdf

    def _crossvalidation_stat(self, title, df, how):
        sdf = pd.DataFrame({
            'mean': df.mean(),
            'std': df.std(),
            'rank': self._rank(df, how).mean(),
        }, columns=['mean', 'std', 'rank']).transpose()
        sdf.index.name = 'type'
        sdf['title'] = title if title else self.dataset.name
        sdf['how'] = how.upper()
        sdf = sdf.reset_index().set_index(['how', 'title', 'type'])
        return sdf

    def show_crossvalidation(self, how='rmse', ignore_estimation_error=False, name=None):
        def save(cdfs, kind):
            if not name:
                return
            basename = '{}_{}_{}'.format(name, how, kind)
            if ignore_estimation_error:
                basename = basename + '_ie'
            filename = self.output.outfilename('collection/results', basename, 'csv')
            cdfs.to_csv(filename)

        titles = self.names
        dfs = [g.show_crossvalidation(how, ignore_estimation_error, '{}_{}'.format(name, how)) for g in self.groups]
        raw = pd.concat([self._crossvalidation_raw(t, d, how) for t, d in zip(titles, dfs)])
        save(raw, 'raw')

        rank = pd.concat([self._crossvalidation_rank(t, d, how) for t, d in zip(titles, dfs)])
        save(rank, 'rank')

        titles = titles + ['total']
        dfs = dfs + [pd.concat(dfs)]
        stat = pd.concat([self._crossvalidation_stat(t, d, how) for t, d in zip(titles, dfs)])
        save(stat, 'stat')
        return stat

    def show_crossvalidation_all(self, ignore_estimation_error=False, name=None):
        metrics = ['dr', 'rmse', 'd', 'ef', 'd1', 'ef1', 'me', 'mae', 'xe', 'm', 'r']
        for how in metrics:
            self.show_crossvalidation(how, ignore_estimation_error, name)

    def show_sensitivity(self, deltas, name=None):
        def raw(title, df):
            sdf = df.copy()
            sdf.index.name = 'delta'
            sdf['title'] = title if title else self.dataset.name
            sdf = sdf.reset_index().set_index(['title', 'delta'])
            return sdf

        def save(cdfs, kind):
            if not name:
                return
            basename = '{}_{}'.format(name, kind)
            filename = self.output.outfilename('collection/sensitivity', basename, 'csv')
            cdfs.to_csv(filename)

        titles = self.names
        dfs = [g.show_sensitivity(deltas, name) for g in self.groups]
        raw = pd.concat([raw(t, d) for t, d in zip(titles, dfs)])
        save(raw, 'raw')
        return raw

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
        l = np.floor(min(np.min(df.Obs), np.min(df.Est)))
        u = np.ceil(max(np.max(df.Obs), np.max(df.Est)))
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
