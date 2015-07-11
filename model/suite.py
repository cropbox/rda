from . import base
from . import multi
from estimation import Ensemble

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import json

class ModelSuiteError(Exception):
    pass

class ModelSuite(base.Model):
    def create(self):
        if not self.dataset.ready():
            raise ModelSuiteError("dataset is not ready: {}".format(self.dataset))
        self._models = self._create()
        return self._models

    def _create(self):
        models = [M(self.dataset) for M in self.ESTIMATORS]

        # calibration
        for m in models:
            #m.calibrate(self.calibrate_years)
            #multi.calibrate(m, self.calibrate_years)
            multi.preset(self.output, self._key_for_coeff(m), m, self.calibrate_years, self.crossvalidate_n)

        # add ensemble models
        e1 = Ensemble(self.dataset)
        e1.use(models, self.calibrate_years, nick='Ensemble', weighted=False)

        e2 = Ensemble(self.dataset)
        e2.use(models, self.calibrate_years, nick='EnsembleW', weighted=True)

        return models + [e1, e2]

    @property
    def models(self):
        return self._models

    @property
    def names(self):
        return [m.name for m in self.models]

    def _key_for_coeff(self, m):
        return base.slugname(
            m.name,
            self.dataset.met_station,
            self.dataset.obs_station,
            self.dataset.name,
            self.dataset.cultivar,
            self.dataset.stage,
            self.calibrate_years,
        )

    def export(self):
        cname = self._key_for_calibration()
        vname = self._key_for_validation()

        self.show_error(self.calibrate_years, name='{}_calibrate'.format(cname))
        self.show_error(self.validate_years, name='{}_validate'.format(vname))

        self.show_prediction(self.export_years, name='{}_single'.format(cname))
        self.show_prediction_multi(self.export_years, name='{}_multi'.format(cname))

        self.plot_prediction(self.calibrate_years, residual=False, name='{}_calibrate_trend'.format(cname))
        self.plot_prediction(self.calibrate_years, residual=True, name='{}_calibrate_residual'.format(cname))
        self.plot_prediction(self.validate_years, residual=False, name='{}_validate_trend'.format(cname))
        self.plot_prediction(self.validate_years, residual=True, name='{}_validate_residual'.format(cname))
        self.plot_prediction(self.export_years, residual=False, name='{}_export_trend'.format(cname))
        self.plot_prediction(self.export_years, residual=True, name='{}_export_residual'.format(cname))

        self.save_param(name='{}_param'.format(cname))

    def show_error(self, years, name=None):
        def errors(how):
            return [m.error(years, how) for m in self.models]
        df = pd.DataFrame({
            'RMSE': errors('rmse'),
            'ME': errors('me'),
            'MAE': errors('mae'),
            'XE': errors('xe'),
            'EF': errors('ef'),
            'D': errors('d'),
            'D1': errors('d1'),
            'Dr': errors('dr'),
        }, index=self.names)
        df.index.name = 'model'

        if name:
            filename = self.output.filename('suite/results', name, 'csv')
            df.to_csv(filename)
        return df

    def show_prediction(self, years, julian=False, name=None):
        m0 = self.models[0]
        x = m0._years(years)
        df = pd.concat(
            [pd.Series(m0.observes(x, julian=julian), index=x)] +
            [pd.Series(m.estimates(x, julian=julian), index=x) for m in self.models],
            keys=['Obs'] + self.names,
            axis=1
        )
        df.index.name = 'year'

        if name:
            filename = self.output.filename('suite/results', name, 'csv')
            df.to_csv(filename)
        return df

    def show_prediction_multi(self, years, name=None):
        m0 = self.models[0]
        x = m0._years(years)

        def observation():
            return pd.DataFrame({
                'model': 'Obs',
                'year': x,
                'day': np.ma.masked_values(m0.observes(x, julian=True), 0)
            })

        def estimation(y):
            df = pd.DataFrame({
                m.name: np.ma.masked_values(m.estimate_multi(y, julian=True), 0) for m in self.models
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

        if name:
            filename = self.output.filename('suite/results', name, 'csv')
            df.to_csv(filename)
        return df

    def plot_prediction(self, years, residual=False, name=None):
        #HACK use first model to populate observation data
        m0 = self.models[0]
        x = m0._years(years)

        # y
        def julian(t):
            try:
                return int(t.strftime('%j'))
            except:
                return np.nan

        def y_obs():
            return np.ma.masked_values(m0.observes(x, julian=True), 0)

        def y_est(m):
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
            [plot_residual(m) for m in self.models]
        else:
            plot_obs()
            [plot_est(m) for m in self.models]

        #plt.legend(loc=9, bbox_to_anchor=(0.5, -0.1))
        plt.legend()
        plt.xlim(*years)

        if name:
            filename = self.output.filename('suite/figures', name, 'png')
            plt.savefig(filename)
        else:
            plt.show()
        plt.close()

    def save_param(self, name):
        filename = self.output.filename('suite/results', name, 'txt')
        with open(filename, 'w') as f:
            for m in self.models:
                f.write('{} : {}\n'.format(m.name, json.dumps(m._coeff)))

    def show_crossvalidation(self, how='rmse', ignore_estimation_error=False, name=None):
        df = pd.DataFrame({
            m.name: m.crossvalidate(self.calibrate_years, how, ignore_estimation_error) for m in self.models
        }, columns=self.names)

        if name:
            filename = self.output.filename('suite/results', name, 'csv')
            df.to_csv(filename)
        return df
