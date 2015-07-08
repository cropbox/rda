from model import Model

import pandas as pd

def create_cherry_dc():
    return Model(
        weather='dc',
        weather_loc='USW00013743',
        observation='cherry_dc',
        observation_loc='DC',
        cultivar=None,
        stage='Peak Bloom',
        calibrate_years=(1991, 2010), # same as Chung et al. (2011)
        validate_years=(1946, 1990),
        export_years=(1946, 2015),
    )

def create_cherry_dc_yoshino():
    return Model(
        weather='dc',
        weather_loc='USW00013743',
        observation='cherry_dc',
        observation_loc='DC',
        cultivar='Yoshino',
        stage='Peak Bloom',
        calibrate_years=(1994, 2014),
        validate_years=(1946, 1993),
        export_years=(1946, 2015),
        MODELS=DEFAULT_MODELS+[DegreeDay, February, March]
    )

def create_cherry_dc_kwanzan():
    return Model(
        weather='dc',
        weather_loc='USW00013743',
        observation='cherry_dc',
        observation_loc='DC',
        cultivar='Yoshino',
        stage='Peak Bloom',
        calibrate_years=(1991, 2011),
        validate_years=(1946, 1990),
        export_years=(1946, 2015),
        MODELS=DEFAULT_MODELS+[DegreeDay, February, March]
    )

def create_apple_kearnesville():
    return Model(
        weather='martinsburg',
        weather_loc='Martinsburg',
        observation='apple_kearneysville',
        observation_loc='Kearneysville',
        cultivar=None,
        stage='Full Bloom',
        calibrate_years=(2001, 2007),
        validate_years=(1997, 2000),
        export_years=(1950, 2010),
    )

def create_apple_kearnesville_self():
    return Model(
        weather='martinsburg',
        weather_loc='Martinsburg',
        observation='apple_kearneysville',
        observation_loc='Kearneysville',
        cultivar=None,
        stage='Full Bloom',
        calibrate_years=(1997, 2007),
        validate_years=(1997, 2007),
        export_years=(1950, 2010),
    )

def create_peach_korea():
    return Model(
        weather='korea_jina',
        weather_loc=None,
        observation='peach_korea',
        observation_loc=None,
        cultivar='Korean Peach',
        stage='FFD',
        calibrate_years=(1998, 2008),
        validate_years=(1982, 1997),
        export_years=(1982, 2010),
    )

def create_pear_korea():
    return Model(
        weather='korea_jina',
        weather_loc=None,
        observation='pear_korea',
        observation_loc=None,
        cultivar='Korean Pear',
        stage='FFD',
        calibrate_years=(1998, 2008),
        validate_years=(1982, 1997),
        export_years=(1982, 2010),
    )

def create_cherry_korea():
    return Model(
        weather='korea_uran',
        weather_loc=None,
        observation='cherry_korea',
        observation_loc=None,
        cultivar='Korean Cherry',
        stage='Full Bloom',
        calibrate_years=(1984, 1994),
        validate_years=(1955, 1983),
        export_years=(1955, 2004),
    )

if __name__ == '__main__':
    models = [
        create_cherry_dc(),
        create_cherry_korea(),
        create_peach_korea(),
        create_pear_korea(),
        create_apple_kearnesville(),
    ]
    cherry_dc, cherry_korea, peach_korea, pear_korea, apple_kearnesville = models

    [m.create(export=True) for m in models]

    pd.concat([m.export_crossvalidate_summaries('rmse') for m in models]).to_csv('results/current/stat_rmse.csv')
    pd.concat([m.export_crossvalidate_summaries('d') for m in models]).to_csv('results/current/stat_d.csv')
    pd.concat([m.export_crossvalidate_summaries('me') for m in models]).to_csv('results/current/stat_me.csv')
    pd.concat([m.export_crossvalidate_summaries('mae') for m in models]).to_csv('results/current/stat_mae.csv')
    pd.concat([m.export_crossvalidate_summaries('xe') for m in models]).to_csv('results/current/stat_xe.csv')
    pd.concat([m.export_crossvalidate_summaries('ef') for m in models]).to_csv('results/current/stat_ef.csv')

    pd.concat([m.export_crossvalidate_summaries('rmse', True) for m in models]).to_csv('results/current/stat_rmse_ie.csv')
    pd.concat([m.export_crossvalidate_summaries('d', True) for m in models]).to_csv('results/current/stat_d_ie.csv')
    pd.concat([m.export_crossvalidate_summaries('me', True) for m in models]).to_csv('results/current/stat_me_ie.csv')
    pd.concat([m.export_crossvalidate_summaries('mae', True) for m in models]).to_csv('results/current/stat_mae_ie.csv')
    pd.concat([m.export_crossvalidate_summaries('xe', True) for m in models]).to_csv('results/current/stat_xe_ie.csv')
    pd.concat([m.export_crossvalidate_summaries('ef', True) for m in models]).to_csv('results/current/stat_ef_ie.csv')
