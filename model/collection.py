from . import base
from util import path

import pandas as pd

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

    def _crossvalidation_stat(self, title, df, how):
        def rank(df):
            if how == 'me':
                df = df.abs()
            higher_is_better = how in {'ef', 'd', 'd1', 'dr'}
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
