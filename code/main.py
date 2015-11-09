from pheno.data.dataset import DataSet
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.model.base import DEFAULT_ESTIMATORS
import pheno.estimation as est

def create_cherry_dc():
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(stage='Peak Bloom')
    return ModelGroup(ds,
        calibrate_years=(1990, 2010), # close to (1991, 2010) from Chung et al. (2011)
        validate_years=[(1946, 1989), (2011, 2014)],
        export_years=(1937, 2015),
    )

def create_cherry_dc_yoshino():
    estimators = DEFAULT_ESTIMATORS + [est.February, est.March]
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar='Yoshino', stage='Peak Bloom')
    return ModelSuite(ds,
        calibrate_years=(1990, 2010),
        validate_years=[(1946, 1989), (2011, 2014)],
        export_years=(1937, 2015),
        ESTIMATORS=estimators,
    )

def create_cherry_dc_kwanzan():
    estimators = DEFAULT_ESTIMATORS + [est.February, est.March]
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar='Kwanzan', stage='Peak Bloom')
    return ModelSuite(ds,
        calibrate_years=(1990, 2010),
        validate_years=[(1946, 1989), (2011, 2014)],
        export_years=(1937, 2015),
        ESTIMATORS=estimators,
    )

def create_apple_kearneysville():
    ds = DataSet('usa_ds3505', 'apple_kearneysville', translator={
        'Kearneysville': 724177,
    }).set(stage='Full Bloom')
    return ModelGroup(ds,
        calibrate_years=(1997, 2007),
        validate_years=(1997, 2007),
        export_years=(1974, 2015),
    )

def create_peach_korea():
    ds = DataSet('korea_shk060', 'peach_korea').set(stage='FFD')
    return ModelGroup(ds,
        calibrate_years=(1988, 2008),
        validate_years=(1974, 1987),
        export_years=(1974, 2010),
    )

def create_pear_korea():
    ds = DataSet('korea_shk060', 'pear_korea').set(stage='FFD')
    return ModelGroup(ds,
        calibrate_years=(1988, 2008),
        validate_years=(1974, 1987),
        export_years=(1974, 2010),
    )

def create_cherry_korea():
    ds = DataSet('korea_shk060', 'cherry_korea').set(stage='Full Bloom')
    return ModelGroup(ds,
        calibrate_years=(1974, 1994),
        validate_years=(1964, 1973),
        export_years=(1964, 2010),
    )

def create_cherry_korea_bloom():
    ds = DataSet('korea_shk060', 'cherry_korea').set(stage='Bloom')
    return ModelGroup(ds,
        calibrate_years=(1984, 2004),
        validate_years=(1974, 1983),
        export_years=(1964, 2010),
    )

def create_garlic_uw(stage, initial_stage):
    estimators = [
        est.GrowingDegree,
        est.BetaFunc,
        est.StandardTemperature,
    ]
    ds = DataSet('uw_garlic', 'garlic_uw').set(stage=stage, initial_stage=initial_stage)
    #HACK: scape appearance was not measured in 2013
    if stage == 'Scape Appearance':
        years = (2014, 2114)
    else:
        years = (2013, 2113, 2014, 2114)
    return ModelGroup(ds,
        calibrate_years=years,
        validate_years=years,
        export_years=years,
        ESTIMATORS=estimators,
    )

def create_default_collection():
    collection = [
        create_cherry_dc(),
        create_cherry_korea(),
        create_peach_korea(),
        create_pear_korea(),
        create_apple_kearneysville(),
    ]
    cherry_dc, cherry_korea, peach_korea, pear_korea, apple_kearneysville = collection
    return collection

def create_garlic_collection():
    return [
        create_garlic_uw('Emergence', 'Planting'),
        create_garlic_uw('Scape Appearance', 'Planting'),
        create_garlic_uw('Estimated Harvest', 'Planting'),
    ]

def create_garlic_collection2():
    return [
        create_garlic_uw('Scape Appearance', 'Emergence'),
        create_garlic_uw('Estimated Harvest', 'Emergence'),
    ]

def show_garlic_collection(mc):
    years = [2013, 2113, 2014, 2114]
    def obs(m):
        return [d.strftime('%Y-%m-%d') for d in m.observes(years)]
    def est(m):
        return [d.strftime('%Y-%m-%d') for d in m.estimates(years)]
    for mg in mc.groups:
        md = mg.models[0]._dataset
        print("* Calibrated from {} to {}".format(md.initial_stage, md.stage))
        print(" - KM: {}".format(obs(mg.models[0])))
        for m in [mg.models[i] for i in [0, 1, 2, 3]]:
            print("   . {}: {}".format(m.name, est(m)))
        print(" - SP: {}".format(obs(mg.models[4])))
        for m in [mg.models[i] for i in [4, 5, 6, 7]]:
            print("   . {}: {}".format(m.name, est(m)))

import pandas as pd
def estimate_garlic_korea(stage, initial_stage):
    estimators = [
        est.GrowingDegree,
        est.BetaFunc,
        est.StandardTemperature,
    ]
    ds = DataSet('korea_garlic', 'garlic_korea').set(stage=stage, initial_stage=initial_stage)
    years = [2010, 2011, 2012]
    mg = ModelGroup(ds,
        calibrate_years=years,
        validate_years=years,
        export_years=years,
        ESTIMATORS=estimators,
    )
    df = pd.concat({ms.dataset.obs_station: ms.show_prediction(years) for ms in mg.suites})
    filename = mg.output.outfilename('group/results', 'KM_{}_{}'.format(stage, initial_stage), 'csv')
    df.to_csv(filename)

if __name__ == '__main__':
    #collection = create_default_collection()
    collection = create_garlic_collection()
    collection = create_garlic_collection2()
    mc = ModelCollection(collection)
    #mc.export()
