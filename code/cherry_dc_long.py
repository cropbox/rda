from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.data.path import Output

# crossvalidation with varying size of dataset

def dataset():
    return DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(stage='Peak Bloom')

def model_group(period, output):
    ds = dataset()
    if period == 10:
        return ModelGroup(ds,
            calibrate_years=(2001, 2010),
            validate_years=[(1946, 1969), (1974, 2000), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        )
    elif period == 20:
        return ModelGroup(ds,
            calibrate_years=(1991, 2010),
            validate_years=[(1946, 1969), (1974, 1990), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        )
    elif period == 30:
        return ModelGroup(ds,
            calibrate_years=(1981, 2010),
            validate_years=[(1946, 1969), (1974, 1980), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        )
    elif period == 40:
        return ModelGroup(ds,
            calibrate_years=(1974, 2010),
            validate_years=[(1946, 1969), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        )
    elif period == 50:
        return ModelGroup(ds,
            calibrate_years=[(1961, 1969), (1974, 2010)],
            validate_years=[(1946, 1960), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        )
    elif period == 60:
        return ModelGroup(ds,
            calibrate_years=[(1951, 1969), (1974, 2010)],
            validate_years=[(1946, 1950), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        )

def model_collection(period, output):
    mg = model_group(period, output)
    return ModelCollection([mg], output)

if __name__ == '__main__':
    output = Output(basepath='../output', timestamp='20160307-cherry-dc-long')
    #periods = [10, 20, 30, 40, 50, 60]
    periods = [20, 30, 40, 50, 60]
    collections = {p: model_collection(p, output) for p in periods}
    [mc.show_crossvalidation_all(
        ignore_estimation_error=True,
        name='crossvalidation_{}'.format(p)
    ) for p, mc in collections.items()]
