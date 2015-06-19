from estimation import *
import multi

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import string
import json
from itertools import product

DEFAULT_MODELS = [
    #GrowingDegreeDay,
    DegreeDay,
    ChillDay,
    BetaFunc,
    Dts,
]

VALID_CHARS = frozenset("-_.() %s%s" % (string.ascii_letters, string.digits))
def _slugify(v):
    return ''.join(c for c in str(v) if c in VALID_CHARS)

def slugname(*args):
    return '_'.join([_slugify(k) for k in args])


class Model(object):
    def __init__(self,
                 weather, weather_loc,
                 observation, observation_loc,
                 cultivar, stage,
                 calibrate_years, validate_years, export_years,
                 crossvalidate_n=1,
                 MODELS=DEFAULT_MODELS):
        self.weather = weather
        self.weather_loc = weather_loc
        self.observation = observation
        self.observation_loc = observation_loc
        self.cultivar = cultivar
        self.stage = stage
        self.calibrate_years = calibrate_years
        self.validate_years = validate_years
        self.export_years = export_years
        self.crossvalidate_n = crossvalidate_n
        self.MODELS = MODELS

        self.load()
        self.create()

    def load(self):
        weather_filename = 'data/{}.pkl'.format(self.weather)
        self.metdf = pd.read_pickle(weather_filename)

        observation_filename = 'data/{}.pkl'.format(self.observation)
        self.obsdf = pd.read_pickle(observation_filename)

    def _create_models(self, o, c):
        # weather
        try:
            w = self.weather_loc if self.weather_loc else o
            mets = self.metdf.loc[w]
        except:
            #HACK: weather data missing for existing observation (i.e. Korean cherry)
            return []

        # observation
        obss = self.obsdf.loc[o, c][self.stage]

        # models
        models = [M(mets, obss) for M in self.MODELS]

        # calibration
        for m in models:
            #m.calibrate(calibrate_years)
            #multi.calibrate(m, calibrate_years)
            name = slugname(m.name, w, o, self.observation, c, self.stage, self.calibrate_years)
            multi.preset(name, m, self.calibrate_years, self.crossvalidate_n)

            #FIXME to be used with check_outlier() and export() functions
            m.weather_loc = w
            m.observation_loc = o
            m.cultivar = c
        # single model plot
        #plot_single_model(models, calibrate_years)
        #plot_single_model(models, calibrate_years, show_as_diff=True)

        # ensemble test
        e1 = Ensemble(mets, obss)
        e1.use(models, self.calibrate_years, nick='Ensemble', weighted=False)

        e2 = Ensemble(mets, obss)
        e2.use(models, self.calibrate_years, nick='EnsembleW', weighted=True)

        models = models + [e1, e2]
        return models

    def _export_models(self, models):
        try:
            m = models[0]
        except:
            return
        w = m.weather_loc
        o = m.observation_loc
        c = m.cultivar
        cname = slugname(self.observation, c, w, o, self.calibrate_years, self.stage)
        vname = slugname(self.observation, c, w, o, self.calibrate_years, self.validate_years, self.stage)

        self.show_single_summary(models, self.calibrate_years).to_csv('results/current/{}_calibrate.csv'.format(cname))
        self.show_single_summary(models, self.validate_years).to_csv('results/current/{}_validate.csv'.format(vname))
        self.export_single_model(models, self.export_years).to_csv('results/current/{}_single.csv'.format(cname))
        self.export_multi_model(models, self.export_years).to_csv('results/current/{}_multi.csv'.format(cname))
        self.export_single_param(models, cname)
        self.plot_single_model(models, self.calibrate_years, False, 'figures/current/{}_calibrate_trend.png'.format(cname))
        self.plot_single_model(models, self.calibrate_years, True, 'figures/current/{}_calibrate_residual.png'.format(cname))
        self.plot_single_model(models, self.validate_years, False, 'figures/current/{}_validate_trend.png'.format(cname))
        self.plot_single_model(models, self.validate_years, True, 'figures/current/{}_validate_residual.png'.format(cname))
        self.plot_single_model(models, self.export_years, False, 'figures/current/{}_export_trend.png'.format(cname))
        self.plot_single_model(models, self.export_years, True, 'figures/current/{}_export_residual.png'.format(cname))

    def create(self, export=False):
        def create_each(o, c):
            models = self._create_models(o, c)
            if export:
                self._export_models(models)
            return models

        # populate available options from observation dataset
        observations = [self.observation_loc] if self.observation_loc else self.obsdf.index.levels[0]
        cultivars = [self.cultivar] if self.cultivar else self.obsdf.index.levels[1]
        ocs = list(product(observations, cultivars))
        self._modelss = [create_each(*oc) for oc in ocs]

        if export:
            self.export()
        return self._modelss

    def export(self):
        def index(m):
            try:
                return '{}_{}'.format(m[0].observation_loc, m[0].cultivar)
            except:
                return ''
        indices = [index(m) for m in self._modelss]

        w = self.weather_loc if self.weather_loc else 'default'
        o = self.observation_loc if self.observation_loc else 'all'
        c = self.cultivar if self.cultivar else 'all'
        cname = slugname(self.observation, c, w, o, self.calibrate_years, self.stage)
        vname = slugname(self.observation, c, w, o, self.calibrate_years, self.validate_years, self.stage)

        self.export_single_summaries(indices, self.calibrate_years, '{}_calibrate'.format(cname))
        self.export_single_summaries(indices, self.validate_years, '{}_validate'.format(vname))
        self.export_single_param_stat('{}_param'.format(cname))


    ####
    def plot_single_model(self, models, years, residual=False, filename=None):
        #HACK use first model to populate observation data
        x = models[0]._years(years)
        obss = models[0]._obss

        # y
        def julian(t):
            try:
                return int(t.strftime('%j'))
            except:
                return np.nan

        def y_obs():
            #return np.array([julian(t) for t in obss[x]])
            return np.ma.masked_values(models[0].observes(x, julian=True), 0)

        def y_est(m):
            #return np.array([julian(t) for t in m.estimates(x)])
            return np.ma.masked_values(m.estimates(x, julian=True), 0)

        # for regular plot
        def plot_obs():
            plt.plot(x, y_obs(), label='Obs')

        def plot_est(m):
            plt.plot(x, y_est(m), '.-', label=m.name)

        # for diff plot
        def plot_zero():
            plt.axhline(0, color='grey', ls=':')

        def plot_residual(m):
            y = y_obs() - y_est(m)
            ls = '--' if m.__class__ is Ensemble else '-'
            lw = 3.0 if m.__class__ is Ensemble else 1.0
            marker = 'o' if m.__class__ is Ensemble else '.'
            alpha = 0.9 if m.__class__ is Ensemble else 0.5
            plt.plot(x, y, ls=ls, lw=lw, marker=marker, alpha=alpha, label=m.name)

        plt.figure()

        if residual:
            plot_zero()
            [plot_residual(m) for m in models]
        else:
            plot_obs()
            [plot_est(m) for m in models]

        #plt.legend(loc=9, bbox_to_anchor=(0.5, -0.1))
        plt.legend()
        plt.xlim(*years)

        if filename:
            plt.savefig(filename)
        #plt.show()
        plt.close()

    def export_single_model(self, models, years):
        x = models[0]._years(years)
        df = pd.concat(
            #[models[0]._obss[x]] +
            [pd.Series(models[0].observes(x), index=x)] +
            [pd.Series(m.estimates(x), index=x) for m in models],
            keys=['Obs'] + [m.name for m in models],
            axis=1
        )
        df.index.name = 'year'
        return df

    def show_single_summary(self, models, years):
        print(" * Years: {}".format(years))
        print(" * Parameters")
        for m in models:
            print("  - {}: {}".format(m.name, m._coeff))
        df = pd.DataFrame({
            'RMSE': [m.error(years, 'rmse') for m in models],
            'ME': [m.error(years, 'me') for m in models],
            'MAE': [m.error(years, 'mae') for m in models],
            'XE': [m.error(years, 'xe') for m in models],
            'EF': [m.error(years, 'ef') for m in models],
            'D': [m.error(years, 'd') for m in models],
        }, index=[m.name for m in models])
        df.index.name = 'model'
        print(df)
        return df

    def export_single_summaries(self, indices, years, name):
        dfs = [self.show_single_summary(models, years) for models in self._modelss]
        df = pd.concat(dfs, keys=indices, names=['index'])
        df.to_csv('results/current/{}_summary.csv'.format(name))

        for k in df.columns:
            plt.figure()
            df.reset_index().pivot(index='index', columns='model', values=k).astype(float).plot(kind='box')
            plt.savefig('figures/current/{}_{}.png'.format(name, k))
            plt.close()
        return df

    def export_crossvalidate_summaries(self, how='rmse', ignore_estimation_error=False):
        def summary(models):
            df = pd.DataFrame({
                m.name: m.crossvalidate(self.calibrate_years, how, ignore_estimation_error) for m in models
            }, columns=[m.name for m in models])
            return df
        df = pd.concat([summary(models) for models in self._modelss])
        #return df
        df = pd.DataFrame({
            'mean': df.mean(),
            'std': df.std(),
        }, ).transpose()
        df.index.name = 'type'
        df['name'] = self.observation
        df['how'] = how.upper()
        df = df.reset_index().set_index(['how', 'name', 'type'])
        return df

    def export_single_param(self, models, name):
        with open('results/current/{}_param.txt'.format(name), 'w') as f:
            for m in models:
                f.write('{} : {}\n'.format(m.name, json.dumps(m._coeff)))

    def export_single_param_stat(self, name):
        models = sum(self._modelss, [])
        names = list({m.name for m in models})
        keys = np.array([m.name for m in models])

        #HACK for Ensemble estimators
        def extract_coeff(m):
            if isinstance(m, Ensemble):
                return dict(zip(['w{}'.format(i) for i in range(m.n)], m._coeff['W']))
            else:
                return m._coeff
        values = np.array([extract_coeff(m) for m in models])

        for n in names:
            df = pd.concat([pd.DataFrame(d, index=[0]) for d in values[keys == n]])
            pd.DataFrame({'mean': df.mean(), 'std': df.std()}).to_csv('results/current/{}_{}.csv'.format(name, n))

    def export_multi_model(self, models, years):
        x = models[0]._years(years)

        def observation():
            return pd.DataFrame({
                'model': 'Obs',
                'year': x,
                'day': np.ma.masked_values(models[0].observes(x, julian=True), 0)
            })

        def estimation(y):
            df = pd.DataFrame({
                m.name: np.ma.masked_values(m.estimate_multi(y, julian=True), 0) for m in models
            })
            df = pd.melt(df, var_name='model', value_name='day').dropna()
            df['year'] = y
            return df

        df = pd.concat(
            [observation()] +
            [estimation(t) for t in x]
        ).dropna()
        df['day'] = df['day'].astype(int)
        df = pd.DataFrame({
            'count': df.groupby(['year','model'])['day'].value_counts()
        }).sort_index()
        df.index.names = ['year', 'model', 'day']
        return df

    def check_outlier(self, threshold=30):
        for models in self._modelss:
            try:
                m = models[0]
            except:
                continue
            print("* {} - {} - {}".format(m.weather_loc, m.observation_loc, m.cultivar))
            for m in models:
                print(" - {}".format(m.name))
                y = np.array(m._years(self.validate_years))
                e = m.error(y)
                i = np.where((np.abs(e) > threshold) == True)
                print(y[i])
                print(e[i])

    def show_outlier_histogram(self, threshold=10, filename=None):
        def outlier(m):
            y = np.array(m._years(self.validate_years))
            e = np.abs(m.error(y))
            i = np.where((e > threshold) == True)
            return e[i]

        outliers = [[outlier(m) for m in models] for models in self._modelss]
        outliers = np.concatenate(sum(outliers, [])).compressed()
        plt.hist(outliers, bins=range(threshold, 40))
        if filename:
            plt.savefig(filename)
        plt.show()
        return outliers
