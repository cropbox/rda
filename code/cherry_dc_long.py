from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.data.path import Output

# crossvalidation with varying size of dataset

def create_cherry_dc_list(output=None):
    ds = DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(stage='Peak Bloom')
    return [
        ModelGroup(ds,
            calibrate_years=(1991, 2010),
            validate_years=[(1946, 1969), (1974, 1990), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        ),
        ModelGroup(ds,
            calibrate_years=(1974, 2010),
            validate_years=[(1946, 1969), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        ),
        ModelGroup(ds,
            calibrate_years=[(1951, 1969), (1974, 2010)],
            validate_years=[(1946, 1950), (2011, 2014)],
            export_years=(1937, 2015),
            output=output,
        ),
    ]

if __name__ == '__main__':
    output = Output(basepath='../output', timestamp='20160301-cherry-dc-long')
    groups = create_cherry_dc_list(output)
    collections = [ModelCollection([g], output) for g in groups]
    [c.export() for c in collections]
