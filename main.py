from model import *

def create_cherry_dc():
    ds = DataSet('dc', 'cherry_dc', mapper={
        'DC': 'USW00013743',
    }).set(stage='Peak Bloom')
    return ModelGroup(ds,
        calibrate_years=(1991, 2010), # same as Chung et al. (2011)
        validate_years=(1946, 1990),
        export_years=(1946, 2015),
    )

def create_cherry_dc_yoshino():
    estimators = base.DEFAULT_ESTIMATORS + [DegreeDay, February, March]
    ds = DataSet('dc', 'cherry_dc', mapper={
        'DC': 'USW00013743',
    }).set(cultivar='Yoshino', stage='Peak Bloom')
    return ModelSuite(ds,
        calibrate_years=(1991, 2010),
        validate_years=(1946, 1990),
        export_years=(1946, 2015),
        ESTIMATORS=estimators,
    )

def create_cherry_dc_kwanzan():
    estimators = base.DEFAULT_ESTIMATORS + [DegreeDay, February, March]
    ds = DataSet('dc', 'cherry_dc', mapper={
        'DC': 'USW00013743',
    }).set(cultivar='Kwanzan', stage='Peak Bloom')
    return ModelSuite(ds,
        calibrate_years=(1991, 2010),
        validate_years=(1946, 1990),
        export_years=(1946, 2015),
        ESTIMATORS=estimators,
    )

def create_apple_kearnesville():
    ds = DataSet('martinsburg', 'apple_kearneysville', mapper={
        'Kearneysville': 'Martinsburg',
    }).set(stage='Full Bloom')
    return ModelGroup(ds,
        calibrate_years=(2001, 2007),
        validate_years=(1997, 2000),
        export_years=(1950, 2010),
    )

def create_apple_kearnesville_self():
    ds = DataSet('martinsburg', 'apple_kearneysville', mapper={
        'Kearneysville': 'Martinsburg',
    }).set(stage='Full Bloom')
    return ModelGroup(ds,
        calibrate_years=(1997, 2007),
        validate_years=(1997, 2007),
        export_years=(1950, 2010),
    )

def create_peach_korea():
    ds = DataSet('korea_jina', 'peach_korea').set(stage='FFD')
    return ModelGroup(ds,
        calibrate_years=(1998, 2008),
        validate_years=(1982, 1997),
        export_years=(1982, 2010),
    )

def create_pear_korea():
    ds = DataSet('korea_jina', 'pear_korea').set(stage='FFD')
    return ModelGroup(ds,
        calibrate_years=(1998, 2008),
        validate_years=(1982, 1997),
        export_years=(1982, 2010),
    )

def create_cherry_korea():
    ds = DataSet('korea_uran', 'cherry_korea').set(stage='Full Bloom')
    return ModelGroup(ds,
        calibrate_years=(1984, 1994),
        validate_years=(1955, 1983),
        export_years=(1955, 2004),
    )

if __name__ == '__main__':
    collection = [
        create_cherry_dc(),
        create_cherry_korea(),
        create_peach_korea(),
        create_pear_korea(),
        create_apple_kearnesville(),
    ]
    cherry_dc, cherry_korea, peach_korea, pear_korea, apple_kearnesville = collection

    mc = ModelCollection(collection)
    mc.export()
