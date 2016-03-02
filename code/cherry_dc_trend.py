from pheno.data.dataset import DataSet
from pheno.model.suite import ModelSuite
from pheno.model.group import ModelGroup
from pheno.model.collection import ModelCollection
from pheno.data.path import Output

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import multiprocessing as mp

# trend analysis with varying window

def _func_cherry_dc_trend(x):
    y, ds, output = x
    return ModelGroup(ds,
        calibrate_years=(y, y+15),
        validate_years=(y+16, y+19),
        export_years=(y, y+19),
        output=output,
    )#.export()

def _func_cherry_dc_trend2(x):
    y, ds, output = x
    return ModelSuite(ds,
        calibrate_years=(y, y+15),
        validate_years=(y+16, y+19),
        export_years=(y, y+19),
        output=output,
    )

def create_cherry_dataset(cultivar=None):
    return DataSet('usa_ds3505', 'cherry_dc', translator={
        'DC': 724050,
    }).set(cultivar=cultivar, stage='Peak Bloom')

def create_cherry_dc_trend(output=None):
    ds = create_cherry_dataset()
    years = range(1946, 1999+1)
    #years = reversed(range(1946, 1999+1))
    with mp.Pool() as p:
        return p.map(_func_cherry_dc_trend, [(y, ds, output) for y in years])
        #return dict(zip(years, p.map(_func_cherry_dc_trend, [(y, ds, output) for y in years])))

def predict_cherry_dc_trend(cultivar, output=None):
    ds = create_cherry_dataset(cultivar)
    years = range(1946, 1999+1)

    def dataframe(y):
        ms = ModelSuite(ds,
            calibrate_years=(y, y+15),
            validate_years=(y+16, y+19),
            export_years=(y, y+19),
            output=output,
        )
        df = ms.show_prediction((1946, 2014), julian=True)
        df = df.reset_index()
        df['base'] = y
        return df.set_index(['base', 'year'])
    return pd.concat([dataframe(y) for y in years])

def metric_cherry_dc_trend(cultivar, max_counts=20, output=None):
    ds = create_cherry_dataset(cultivar)
    years = range(1946, 1999+1)
    # years = range(1946, 1999+1, 3)
    # years = range(1947, 1999+1, 3)
    # years = range(1948, 1999+1, 3)

    def dataframe(y):
        ms = ModelSuite(ds,
            calibrate_years=(y, y+15),
            validate_years=(y+16, y+19),
            export_years=(y, y+19),
            output=output,
        )
        counts = min(max_counts, max(0, 2014 - (y+16) + 1))
        if counts == 0:
            return None
        def metric(y, i):
            df = ms.show_metric((y+16, y+16+i))
            df = df.reset_index()
            df['base'] = y
            df['count'] = i+1
            return df.set_index(['base', 'model', 'count'])
        df = pd.concat([metric(y, i) for i in range(counts)])
        df.to_csv(output.outfilename('results/{}'.format(cultivar), str(y), 'csv'))
        return df
    df = pd.concat([dataframe(y) for y in years])
    df.to_csv(output.outfilename('results/{}'.format(cultivar), cultivar, 'csv'))
    return df

def plot_cherry_dc_trend(df, cultivar, output):
    #csvname = output.outfilename('results/{}'.format(cultivar), cultivar, 'csv')
    #df = pd.read_csv(csvname, na_values=['--'])
    #sns.boxplot(x='count', y='D', hue='model', data=df)
    metrics = df.columns[3:]
    for m in metrics:
        g = sns.FacetGrid(df, col='model', col_wrap=6)
        g.map(sns.boxplot, 'count', m)
        plt.savefig(output.outfilename('results/{}'.format(cultivar), m, 'png'))

if __name__ == '__main__':
    output = Output(basepath='../output', timestamp='20160127-cherry-dc-trend')

    #create_cherry_dc_trend(output)

    #df = predict_cherry_dc_trend('Yoshino', output)
    #df = predict_cherry_dc_trend('Kwanzan', output)

    # ds = create_cherry_dataset('Yoshino')
    # ds.observation().apply(lambda x: int(x.strftime('%j'))).mean()
    # ds.observation().apply(lambda x: int(x.strftime('%j'))).std()
    # df.mean()
    # df.std()

    df = metric_cherry_dc_trend('Yoshino', 20, output)
    plot_cherry_dc_trend(df, 'Yoshino', output)

    df = metric_cherry_dc_trend('Kwanzan', 20, output)
    plot_cherry_dc_trend(df, 'Kwanzan', output)
