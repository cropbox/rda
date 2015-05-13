from estimation import *
import multi

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#############
# Model Run #
#############

DEFAULT_MODELS = [
    GrowingDegreeDay,
    ChillDay,
    BetaFunc,
    Dts,
]

def run(weather_filename, location, observation_filename, cultivar, stage, years, n=3, MODELS=DEFAULT_MODELS):
    # weather
    mets = pd.read_pickle(weather_filename).loc[location]

    # observation
    obss = pd.read_pickle(observation_filename).loc[cultivar][stage]

    # models
    models = [m(mets, obss) for m in MODELS]
    #dd, cd, bf, dt = models

    # calibration
    for m in models:
        #m.calibrate(years)
        #multi.calibrate(m, years)
        multi.preset(m, location, cultivar, stage, years, n)
    # single model plot
    #plot_single_model(models, years)
    #plot_single_model(models, years, show_as_diff=True)
    return models

################
# Single Model #
################

def plot_single_model(models, years, show_as_diff=False):
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
        return np.array([julian(t) for t in obss[x]])

    def y_est(m):
        return np.array([julian(t) for t in m.estimates(x)])

    # for regular plot
    def plot_obs():
        plt.plot(x, y_obs(), label='Obs')

    def plot_est(m):
        plt.plot(x, y_est(m), '.', label=m.name)

    # for diff plot
    def plot_zero():
        plt.axhline(0)

    def plot_diff(m):
        y = y_est(m) - y_obs()
        plt.plot(x, y, '.', label=m.name)

    if show_as_diff:
        plot_zero()
        [plot_diff(m) for m in models]
    else:
        plot_obs()
        [plot_est(m) for m in models]

    plt.legend()
    plt.xlim(*years)
    plt.show()

def export_single_model(models, years):
    x = models[0]._years(years)
    df = pd.concat(
        [models[0]._obss[x]] +
        [pd.Series(m.estimates(x), index=x) for m in models],
        keys=['Obs'] + [m.name for m in models],
        axis=1
    )
    df.index.name = 'year'
    return df

###############
# Multi Model #
###############

def export_multi_model(models, years):
    x = models[0]._years(years)

    def observation():
        return pd.DataFrame({
            'model': 'Obs',
            'day': models[0]._obss[x].dropna().apply(lambda x: int(x.strftime('%j'))),
        }).reset_index()

    def estimation(y):
        df = pd.DataFrame({m.name: m.estimate_multi(y) for m in models})
        df = pd.melt(df, var_name='model', value_name='day').dropna()
        df['year'] = y
        df['day'] = df['day'].astype(int)
        return df

    df = pd.concat(
        [observation()] +
        [estimation(t) for t in x]
    )
    df = pd.DataFrame({
        'count': df.groupby(['year','model'])['day'].value_counts()
    }).sort_index()
    df.index.names = ['year', 'model', 'day']
    return df

def export_multi_model2(models, years):
    x = models[0]._years(years)

    def observation():
        s = models[0]._obss[x].value_counts()
        df = pd.DataFrame(s).reset_index()
        df.columns = ['day', 'count']
        df['year'] = df['day'].apply(lambda x: int(x.strftime('%Y')))
        df['day'] = df['day'].apply(lambda x: int(x.strftime('%j')))
        df['model'] = 'Obs'
        return df.set_index(['year', 'model', 'day'])

    def estimation(m, y):
        s = m.estimate_multi2(y)
        s.index = [int(t.strftime('%j')) for t in s.index]
        return s

    def combine(ss, y):
        df = pd.DataFrame(ss)
        df.index.name = 'day'
        df['year'] = y
        return pd.melt(df.reset_index(),
                     id_vars=['year', 'day'],
                     var_name='model',
                     value_name='count',
        ).dropna().set_index(['year', 'model', 'day'])

    return pd.concat(
        [observation()] +
        [combine({m.name: estimation(m, t) for m in models}, t) for t in x]
    ).dropna().sort_index()

def main():
    # Cherry
    weather_filename = 'data/dc.pkl'
    location = 'USW00013743'
    observation_filename = 'data/cherry_dc.pkl'
    stage = 'Peak Bloom'
    export_years = (1946, 2015)

    # Cherry - Yoshino
    cultivar = 'Yoshino'
    years = (1994, 2014)
    models = run(weather_filename, location, observation_filename, cultivar, stage, years, MODELS=DEFAULT_MODELS+[DegreeDay, February, March])
    export_single_model(models, export_years).to_csv('cherry_yoshino.csv')
    export_multi_model(models, export_years).to_csv('cherry_yoshino_multi.csv')

    # Cherry - Yoshino
    cultivar = 'Kwanzan'
    years = (1991, 2011)
    models = run(weather_filename, location, observation_filename, cultivar, stage, years, MODELS=DEFAULT_MODELS+[March])
    export_single_model(models, export_years).to_csv('cherry_kwanzan.csv')
    export_multi_model(models, export_years).to_csv('cherry_kwanzan_multi.csv')

    # Apple
    weather_filename = 'data/martinsburg.pkl'
    location = 'Martinsburg'
    observation_filename = 'data/apple_kearneysville.pkl'
    stage = 'Full Bloom'
    years = (1997, 2007)
    export_years = (1950, 2010)

    # Apple - Fuji
    cultivar = '11 Fuji, Red Sport # 2'
    models = run(weather_filename, location, observation_filename, cultivar, stage, years, n=3)
    export_single_model(models, export_years).to_csv('apple_fuji.csv')
    export_multi_model(models, export_years).to_csv('apple_fuji_multi.csv')

    # Apple - Honeycrisp
    cultivar = '16 Honeycrisp/M.9'
    models = run(weather_filename, location, observation_filename, cultivar, stage, years, n=3)
    export_single_model(models, export_years).to_csv('apple_honeycrisp.csv')
    export_multi_model(models, export_years).to_csv('apple_honeycrisp_multi.csv')

if __name__ == '__main__':
    main()
    #df.xs('DegreeDays', level='model')
    pass
