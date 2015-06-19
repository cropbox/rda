import numpy as np
import pandas as pd
import datetime

class Benchmark(object):
    def __init__(self, model):
        self.model = model

    def compare(self, years, coeffs=None, names=None, form=None):
        years = self.model._years(years)

        if coeffs is None:
            coeffs = [self.model._coeff]
        elif type(coeffs) is not list:
            coeffs = [coeffs]

        columns = ['Observation']
        C = len(coeffs)
        if not names:
            names = ['Estimation'+str(i) for i in range(C)]
        columns = ['Observation'] + names

        res = pd.DataFrame(index=years, columns=columns)
        for year in years:
            for i, coeff in enumerate(coeffs):
                try:
                    est = self.model.estimate(year, coeff)
                    obs = self.model.observe(year)
                    diff = est - obs
                except:
                    est = None
                    obs = None
                    diff = datetime.timedelta(days=0)
                res['Observation'][year] = obs
                res.iloc[:, i+1][year] = est

        if form == 'diff':
            return self._show_diff(res)
        elif form == 'summary':
            return self._show_summary(res)
        else:
            return res

    @staticmethod
    def _show_diff(res):
        ests = res.columns[1:]
        return pd.DataFrame([(res.ix[:,c] - res.ix[:,0]) for c in ests], index=ests).transpose()

    @classmethod
    def _show_summary(cls, res):
        err = cls._show_diff(res).apply(lambda x: abs(x) / np.timedelta64(1, 'D'))
        return pd.DataFrame({
            'Total': err.sum(),
            'RMSE': err.apply(lambda x: np.sqrt((x**2).sum() / len(err))),
            'MAE': err.sum() / len(err),
            'XE': err.max(),
        })

    def cross_validate(self, years):
        years = self.model._years(years)
        def rmse(year):
            train_years = set(years) - {year}
            try:
                coeff = self.model.calibrate(train_years)
                res = self.compare(year, coeff)
                return self._show_summary(res)['RMSE'][0]
            except:
                return -1
        return np.ma.masked_values([rmse(y) for y in years], -1)

    @classmethod
    def validate(cls, mets, obss, years, MODELS=[DegreeDays, ChillDays, BetaFunc, Dts]):
        def rmse(M):
            rmses = cls(M(mets, obss)).cross_validate(years)
            return {
                'Mean': rmses.mean(),
                'Std': rmses.std(),
            }
        return pd.DataFrame({M.__name__: rmse(M) for M in MODELS})

    @classmethod
    def validate2(cls, mets, obss, years, MODELS=[DegreeDays, ChillDays, BetaFunc, Dts]):
        return pd.DataFrame({
            M.__name__: pd.Series(
                cls(M(mets, obss)).cross_validate(years),
                cls(M(mets, obss)).model._years(years)
            ) for M in MODELS})

    @classmethod
    def validate_all(cls, mets, pheno, years):
        return {c: cls.validate2(mets, pheno.loc[c], years) for c in pheno.index.levels[0]}
