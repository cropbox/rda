from estimation import *
import multi

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from itertools import product

##############
# Model Init #
##############

DEFAULT_MODELS = [
    GrowingDegreeDay,
    ChillDay,
    BetaFunc,
    Dts,
]

def init(weather_filename, location, observation_filename, cultivar, stage, years, n=3, MODELS=DEFAULT_MODELS):
    # weather
    mets = pd.read_pickle(weather_filename).loc[location]

    # observation
    obsdf = pd.read_pickle(observation_filename)
    #HACK: some local datasets missing station code
    if 'station' in obsdf.index.names:
        obsdf = obsdf.loc[location]
    obss = obsdf.loc[cultivar][stage]

    # models
    models = [m(mets, obss) for m in MODELS]
    #dd, cd, bf, dt = models

    # calibration
    for m in models:
        #m.calibrate(years)
        #multi.calibrate(m, years)
        multi.preset(m, location, '', '', cultivar, stage, years, n)
    # single model plot
    #plot_single_model(models, years)
    #plot_single_model(models, years, show_as_diff=True)

    # ensemble test
    e1 = Ensemble(mets, obss)
    e1.use(models, 'Ensemble')

    e2 = Ensemble(mets, obss)
    e2.use(models, 'EnsembleW')
    e2.calibrate(years)

    models = models + [e1, e2]

    return models

################
# Single Model #
################

def plot_single_model(models, years, show_as_diff=False, filename=None):
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
        plt.plot(x, y_est(m), '.-', label=m.name)

    # for diff plot
    def plot_zero():
        plt.axhline(0, color='grey', ls=':')

    def plot_diff(m):
        y = y_est(m) - y_obs()
        ls = '--' if m.__class__ is Ensemble else '-'
        lw = 3.0 if m.__class__ is Ensemble else 1.0
        marker = 'o' if m.__class__ is Ensemble else '.'
        alpha = 0.9 if m.__class__ is Ensemble else 0.5
        plt.plot(x, y, ls=ls, lw=lw, marker=marker, alpha=alpha, label=m.name)

    plt.figure()

    if show_as_diff:
        plot_zero()
        [plot_diff(m) for m in models]
    else:
        plot_obs()
        [plot_est(m) for m in models]

    #plt.legend(loc=9, bbox_to_anchor=(0.5, -0.1))
    plt.legend()
    plt.xlim(*years)

    if filename:
        plt.savefig(filename)
    #plt.show()

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

def show_single_summary(models, years):
    print " * Years: {}".format(years)
    print " * Parameters"
    for m in models:
        print "  - {}: {}".format(m.name, m._coeff)
    df = pd.DataFrame({
        'RMSE': [m.error(years, 'rmse') for m in models],
        'ME': [m.error(years, 'me') for m in models],
        'MAE': [m.error(years, 'mae') for m in models],
        'XE': [m.error(years, 'xe') for m in models],
        'EF': [m.error(years, 'ef') for m in models],
        'D': [m.error(years, 'd') for m in models],
    }, index=[m.name for m in models])
    df.index.name = 'model'
    print df
    return df

def export_single_summaries(indices, modelss, years, name):
    dfs = [show_single_summary(models, years) for models in modelss]
    df = pd.concat(dfs, keys=indices, names=['index'])
    df.to_csv('{}_summary.csv'.format(name))

    for k in df.columns:
        df.reset_index().pivot(index='index', columns='model', values=k).plot(kind='box')
        plt.savefig('{}_{}.png'.format(name, k))
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
    models = init(weather_filename, location, observation_filename, cultivar, stage, years, MODELS=DEFAULT_MODELS+[DegreeDay, February, March])
    show_single_summary(models, years)
    export_single_model(models, export_years).to_csv('cherry_yoshino.csv')
    export_multi_model(models, export_years).to_csv('cherry_yoshino_multi.csv')
    plot_single_model(models, years, True, 'cherry_yoshino.png')

    # Cherry - Yoshino
    cultivar = 'Kwanzan'
    years = (1991, 2011)
    models = init(weather_filename, location, observation_filename, cultivar, stage, years, MODELS=DEFAULT_MODELS+[DegreeDay, February, March])
    show_single_summary(models, years)
    export_single_model(models, export_years).to_csv('cherry_kwanzan.csv')
    export_multi_model(models, export_years).to_csv('cherry_kwanzan_multi.csv')
    plot_single_model(models, years, True, 'cherry_kwanzan.png')

    # Apple
    weather_filename = 'data/martinsburg.pkl'
    location = 'Martinsburg'
    observation_filename = 'data/apple_kearneysville.pkl'
    stage = 'Full Bloom'
    years = (1997, 2007)
    export_years = (1950, 2010)

    # Apple - Fuji
    cultivar = '11 Fuji, Red Sport # 2'
    models = init(weather_filename, location, observation_filename, cultivar, stage, years, n=3)
    show_single_summary(models, years)
    export_single_model(models, export_years).to_csv('apple_fuji.csv')
    export_multi_model(models, export_years).to_csv('apple_fuji_multi.csv')
    plot_single_model(models, years, True, 'apple_fuji.png')

    # Apple - Honeycrisp
    cultivar = '16 Honeycrisp/M.9'
    models = init(weather_filename, location, observation_filename, cultivar, stage, years, n=3)
    show_single_summary(models, years)
    export_single_model(models, export_years).to_csv('apple_honeycrisp.csv')
    export_multi_model(models, export_years).to_csv('apple_honeycrisp_multi.csv')
    plot_single_model(models, years, True, 'apple_honeycrisp.png')

    # Korea (from Dr. Jina Hur)
    weather_filename = 'data/korea_jina.pkl'
    location = 295 # Namhae
    stage = 'FFD'
    years = (1998, 2008)
    export_years = (1982, 2010)

    # Peach (Korean)
    observation_filename = 'data/peach_korea.pkl'
    cultivar = 'Korean Peach'
    models = init(weather_filename, location, observation_filename, cultivar, stage, years, n=3)
    show_single_summary(models, years)
    export_single_model(models, export_years).to_csv('peach_namhae.csv')
    export_multi_model(models, export_years).to_csv('peach_namhae_multi.csv')
    plot_single_model(models, years, True, 'peach_namhae.png')

    # Pear (Korean)
    observation_filename = 'data/pear_korea.pkl'
    cultivar = 'Korean Pear'
    models = init(weather_filename, location, observation_filename, cultivar, stage, years, n=3)
    show_single_summary(models, years)
    export_single_model(models, export_years).to_csv('pear_namhae.csv')
    export_multi_model(models, export_years).to_csv('pear_namhae_multi.csv')
    plot_single_model(models, years, True, 'pear_namhae.png')

    # Cherry (Korean) (from Dr. Uran Chung)
    weather_filename = 'data/korea_uran.pkl'
    location = 184 # Jeju
    observation_filename = 'data/cherry_korea.pkl'
    cultivar = 'Korean Cherry'
    stage = 'Full Bloom'
    years = (1984, 1994)
    export_years = (1984, 2004)
    models = init(weather_filename, location, observation_filename, cultivar, stage, years, n=3)
    show_single_summary(models, years)
    export_single_model(models, export_years).to_csv('cherry_jeju.csv')
    export_multi_model(models, export_years).to_csv('cherry_jeju_multi.csv')
    plot_single_model(models, years, True, 'cherry_jeju.png')

import string
VALID_CHARS = frozenset("-_.() %s%s" % (string.ascii_letters, string.digits))
def _slugify(v):
    return ''.join(c for c in str(v) if c in VALID_CHARS)

#def slugname(model, weather_loc, observation_loc, species, cultivar, stage, years):
    #keys = [model.name, weather_loc, observation_loc, species, cultivar, stage, years]
    #keys = [_slugify(k) for k in keys]
    #return '_'.join(keys)
def slugname(*args):
    return '_'.join([_slugify(k) for k in args])

def run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years, n=3, MODELS=DEFAULT_MODELS):
    metdf = pd.read_pickle(weather_filename)
    obsdf = pd.read_pickle(observation_filename)

    def run_each(o, c):
        # weather
        try:
            w = weather_loc if weather_loc else o
            mets = metdf.loc[w]
        except:
            #HACK: weather data missing for existing observation (i.e. Korean cherry)
            return

        # observation
        obss = obsdf.loc[o, c][stage]

        # models
        models = [m(mets, obss) for m in MODELS]

        # calibration
        for m in models:
            #m.calibrate(calibrate_years)
            #multi.calibrate(m, calibrate_years)
            multi.preset(slugname(m.name, w, o, species, c, stage, calibrate_years), m, calibrate_years, n)
        # single model plot
        #plot_single_model(models, calibrate_years)
        #plot_single_model(models, calibrate_years, show_as_diff=True)

        # ensemble test
        e1 = Ensemble(mets, obss)
        e1.use(models, 'Ensemble')

        e2 = Ensemble(mets, obss)
        e2.use(models, 'EnsembleW')
        e2.calibrate(calibrate_years)

        models = models + [e1, e2]

        name = slugname(species, c, w, o, calibrate_years, stage)
        name2 = slugname(species, c, w, o, calibrate_years, validate_years, stage)
        show_single_summary(models, calibrate_years).to_csv('{}_calibrate.csv'.format(name))
        show_single_summary(models, validate_years).to_csv('{}_validate.csv'.format(name2))
        export_single_model(models, export_years).to_csv('{}_single.csv'.format(name))
        export_multi_model(models, export_years).to_csv('{}_multi.csv'.format(name))
        plot_single_model(models, calibrate_years, True, '{}_calibrate.png'.format(name))
        plot_single_model(models, validate_years, True, '{}_validate.png'.format(name))
        plot_single_model(models, export_years, True, '{}_export.png'.format(name))

        return models

    # populate available options from observation dataset
    observations = [observation_loc] if observation_loc else obsdf.index.levels[0]
    cultivars = [cultivar] if cultivar else obsdf.index.levels[1]
    ocs = list(product(observations, cultivars))
    modelss = [run_each(*oc) for oc in ocs]

    indices = ['_'.join(str(oc)) for oc in ocs]
    export_single_summaries(indices, modelss, calibrate_years, '{}_calibrate'.format(slugname(species, calibrate_years, stage)))
    export_single_summaries(indices, modelss, validate_years, '{}_validate'.format(slugname(species, calibrate_years, validate_years, stage)))
    return modelss

def main2():
    # Cherry (DC)
    weather_filename = 'data/dc.pkl'
    weather_loc = 'USW00013743'
    observation_filename = 'data/cherry_dc.pkl'
    observation_loc = 'DC'
    species = 'cherry'
    stage = 'Peak Bloom'
    export_years = (1946, 2015)

    # Cherry (DC) - Yoshino
    cultivar = 'Yoshino'
    calibrate_years = (1994, 2014)
    validate_years = (1946, 1993)
    run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years, MODELS=DEFAULT_MODELS+[DegreeDay, February, March])

    # Cherry (DC) - Kwanzan
    cultivar = 'Kwanzan'
    calibrate_years = (1991, 2011)
    validate_years = (1946, 1990)
    run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years, MODELS=DEFAULT_MODELS+[DegreeDay, February, March])

    # Apple
    weather_filename = 'data/martinsburg.pkl'
    weather_loc = 'Martinsburg'
    observation_filename = 'data/apple_kearneysville.pkl'
    observation_loc = 'Kearneysville'
    species = 'apple'
    cultivar = None
    stage = 'Full Bloom'
    calibrate_years = (1997, 2007)
    validate_years = calibrate_years
    export_years = (1950, 2010)
    run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years)

    calibrate_years = (2001, 2007)
    validate_years = (1997, 2000)
    export_years = (1950, 2010)
    run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years)

    # Korea (from Dr. Jina Hur)
    weather_filename = 'data/korea_jina.pkl'
    weather_loc = None
    stage = 'FFD'
    calibrate_years = (1998, 2008)
    validate_years = (1982, 1997)
    export_years = (1982, 2010)

    # Peach (Korean)
    observation_filename = 'data/peach_korea.pkl'
    observation_loc = None
    species = 'peach'
    cultivar = 'Korean Peach'
    run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years)

    # Pear (Korean)
    observation_filename = 'data/pear_korea.pkl'
    observation_loc = None
    species = 'pear'
    cultivar = 'Korean Pear'
    run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years)

    # Cherry (Korean) (from Dr. Uran Chung)
    weather_filename = 'data/korea_uran.pkl'
    weather_loc = None
    observation_filename = 'data/cherry_korea.pkl'
    observation_loc = None
    species = 'cherry'
    cultivar = 'Korean Cherry'
    stage = 'Full Bloom'
    calibrate_years = (1984, 1994)
    validate_years = (1955, 1983)
    export_years = (1955, 2004)
    run(weather_filename, weather_loc, observation_filename, observation_loc, species, cultivar, stage, calibrate_years, validate_years, export_years)

if __name__ == '__main__':
    main()
    #df.xs('DegreeDays', level='model')
    pass
