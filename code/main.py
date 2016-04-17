from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.model.base import DEFAULT_ESTIMATORS
from pheno.data.path import Output
import pheno.estimation as est

output = Output(timestamp='current')

def create_cherry_dc():
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(stage='Peak Bloom')
    return ModelGroup(ds,
        calibrate_years=(1991, 2010), # same as (1991, 2010) from Chung et al. (2011)
        validate_years=[(1946, 1990), (2011, 2014)],
        export_years=(1937, 2015),
        output=output,
    )

def create_cherry_dc_yoshino():
    estimators = DEFAULT_ESTIMATORS + [est.February, est.March]
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar='Yoshino', stage='Peak Bloom')
    return ModelSuite(ds,
        calibrate_years=(1991, 2010),
        validate_years=[(1946, 1990), (2011, 2014)],
        export_years=(1937, 2015),
        ESTIMATORS=estimators,
        output=output,
    )

def create_cherry_dc_kwanzan():
    estimators = DEFAULT_ESTIMATORS + [est.February, est.March]
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar='Kwanzan', stage='Peak Bloom')
    return ModelSuite(ds,
        calibrate_years=(1991, 2010),
        validate_years=[(1946, 1990), (2011, 2014)],
        export_years=(1937, 2015),
        ESTIMATORS=estimators,
        output=output,
    )

def create_apple_kearneysville():
    ds = DataSet('usa_ds3505', 'apple_kearneysville', translator={
        'Kearneysville': 724177,
    }).set(stage='Full Bloom')
    return ModelGroup(ds,
        calibrate_years=(1997, 2006),
        validate_years=[2007],
        export_years=(1974, 2015),
        output=output,
    )

def create_peach_korea():
    ds = DataSet('korea_shk060', 'peach_korea').set(stage='FFD')
    return ModelGroup(ds,
        calibrate_years=(1989, 2008),
        validate_years=(1974, 1988),
        export_years=(1974, 2010),
        output=output,
    )

def create_pear_korea():
    ds = DataSet('korea_shk060', 'pear_korea').set(stage='FFD')
    return ModelGroup(ds,
        calibrate_years=(1989, 2008),
        validate_years=(1974, 1988),
        export_years=(1974, 2010),
        output=output,
    )

def create_cherry_korea():
    ds = DataSet('korea_shk060', 'cherry_korea').set(stage='Full Bloom')
    return ModelGroup(ds,
        calibrate_years=(1975, 1994),
        validate_years=(1964, 1974),
        export_years=(1964, 2010),
        output=output,
    )

def create_cherry_korea_bloom():
    ds = DataSet('korea_shk060', 'cherry_korea').set(stage='Bloom')
    return ModelGroup(ds,
        calibrate_years=(1985, 2004),
        validate_years=(1974, 1984),
        export_years=(1964, 2010),
        output=output,
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
