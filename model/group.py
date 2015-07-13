from . import base
from .suite import ModelSuite, ModelSuiteError

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from itertools import product
from collections import OrderedDict

class ModelGroupError(Exception):
    pass

class ModelGroup(base.Model):
    def create(self):
        self._suites = self._create()
        return self._suites

    def _create(self):
        # populate available options from observation dataset
        observations = self.dataset.obs_stations()
        cultivars = self.dataset.cultivars()
        ocs = product(observations, cultivars)

        def suite(o, c):
            try:
                return ModelSuite(
                    self.dataset.copy().set(obs_station=o, cultivar=c),
                    self.calibrate_years, self.validate_years, self.export_years,
                    self.crossvalidate_n, self.ESTIMATORS,
                    self.output,
                )
            except ModelSuiteError as e:
                return None
        return OrderedDict((k, suite(*k)) for k in ocs)

    @property
    def suites(self):
        return [s for s in self._suites.values() if s is not None]

    @property
    def models(self):
        return sum([[m for m in s.models] for s in self.suites], [])

    @property
    def indices(self):
        def index(ds):
            return '{}_{}'.format(ds.obs_station, ds.cultivar)
        return [index(s.dataset) for s in self.suites]

    def export(self):
        # export results for all model suites
        [s.export() for s in self.suites]

        # export group-level results
        cname = self._key_for_calibration()
        vname = self._key_for_validation()

        self.save_metric_stat(self.calibrate_years, name='{}_calibrate'.format(cname))
        self.save_metric_stat(self.validate_years, name='{}_validate'.format(vname))

        self.show_predictions(self.export_years, julian=True, name='{}_singles'.format(cname))

        self.save_param_stat(name='{}_param'.format(cname))

        self.plot_outlier_histogram(lower=10, upper=40, name='{}_outlier'.format(vname))

    def _metrics(self, years):
        return pd.concat(
            [s.show_metric(years) for s in self.suites],
            keys=self.indices,
            names=['index']
        )

    def show_metric_stat(self, years, name=None, df=None):
        if df is None:
            df = self._metrics(years)
        if name:
            filename = self.output.outfilename('group/results', '{}_summary'.format(name), 'csv')
            df.to_csv(filename)
        return df

    def plot_metric_stat(self, years, name=None, df=None):
        if df is None:
            df = self._metrics(years)
        for k in df.columns:
            fig = plt.figure()
            df.reset_index().pivot(index='index', columns='model', values=k).astype(float).plot(kind='box')
            if name:
                filename = self.output.outfilename('group/figures', '{}_{}'.format(name, k), 'png')
                plt.savefig(filename)
            else:
                plt.show()
            plt.close(fig)
        return df

    def save_metric_stat(self, years, name):
        df = self.show_metric_stat(years, name)
        self.plot_metric_stat(years, name, df)

    def show_predictions(self, years, julian=False, exclude_ensembles=False, name=None):
        # for Jennifer's plot
        df = pd.concat([s.show_prediction(years, julian, exclude_ensembles) for s in self.suites])

        if name:
            filename = self.output.outfilename('group/results', name, 'csv')
            df.to_csv(filename)
        return df

    def plot_obs_vs_est(self, years=None, exclude_ensembles=True, name=None):
        if years is None:
            years = self.dataset.validate_years
        df = pd.melt(
            self.show_predictions(years, julian=True, exclude_ensembles=exclude_ensembles).reset_index(),
            id_vars=['year', 'Obs'], var_name='model', value_name='Est'
        )
        l = np.floor(min(min(df.Obs), min(df.Est)))
        u = np.ceil(max(max(df.Obs), max(df.Est)))
        sns.jointplot(x='Obs', y='Est', data=df, xlim=(l,u), ylim=(l,u), kind='reg')
        sns.plt.plot([l,u], [l,u], '--')
        sns.plt.show()
        return df

    def save_param_stat(self, name):
        models = self.models
        name_indices = np.array([m.name for m in models])
        cultivar_indices = np.array(sum([[s.dataset.cultivar] * len(s.models) for s in self.suites], []))
        names = list(set(name_indices))
        cultivars = list(set(cultivar_indices))
        values = np.array([m.coeff for m in models])

        def construct(n, c):
            df = pd.concat([pd.DataFrame(d, index=[0]) for d in values[(name_indices == n) * (cultivar_indices == c)]])
            df = pd.DataFrame({'mean': df.mean(), 'std': df.std()}, columns=['mean', 'std']).transpose()
            df.index.name = 'type'
            df['model'] = n
            df['cultivar'] = c
            return df.reset_index().set_index(['model', 'cultivar', 'type'])

        for n in names:
            df = pd.concat([construct(n, c) for c in cultivars])
            filename = self.output.outfilename('group/results', '{}_{}'.format(name, n), 'csv')
            df.to_csv(filename)

    def _outlier(self, m, threshold):
        y = np.array(m._years(self.validate_years))
        e = np.abs(m.metric(y))
        i = np.where((e > threshold) == True)
        return y, e, i

    def check_outlier(self, threshold=30):
        for s in self.suites:
            ds = s.dataset
            print("* {} - {} - {}".format(ds.met_station, ds.obs_station, ds.cultivar))
            for m in s.models:
                print(" - {}".format(m.name))
                y, e, i = self._outlier(m, threshold)
                print(y[i])
                print(e[i])

    def plot_outlier_histogram(self, lower=10, upper=40, name=None):
        fig = plt.figure()

        def outlier(m):
            y, e, i = self._outlier(m, lower)
            return e[i]
        o = [[outlier(m) for m in s.models] for s in self.suites]
        o = np.concatenate(sum(o, [])).compressed()
        plt.hist(o, bins=range(lower, upper))

        if name:
            filename = self.output.outfilename('group/figures', name, 'png')
            plt.savefig(filename)
        else:
            plt.show()
        plt.close(fig)
        return o

    def show_crossvalidation(self, how='rmse', ignore_estimation_error=False, name=None):
        df = pd.concat([s.show_crossvalidation(how, ignore_estimation_error) for s in self.suites])

        if name:
            filename = self.output.outfilename('group/results', name, 'csv')
            df.to_csv(filename)
        return df
