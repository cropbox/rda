from pheno.data.dataset import DataSet
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.model.base import DEFAULT_ESTIMATORS

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
    estimators = DEFAULT_ESTIMATORS + [February, March]
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
    estimators = DEFAULT_ESTIMATORS + [February, March]
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
        calibrate_years=(1984, 2004),
        validate_years=(1974, 1983),
        export_years=(1974, 2010),
    )

if __name__ == '__main__':
    collection = [
        create_cherry_dc(),
        create_cherry_korea(),
        create_peach_korea(),
        create_pear_korea(),
        create_apple_kearneysville(),
    ]
    cherry_dc, cherry_korea, peach_korea, pear_korea, apple_kearneysville = collection

    mc = ModelCollection(collection)
    mc.export()
