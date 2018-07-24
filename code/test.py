from pheno.data.dataset import DataSet

ds = DataSet('usa_ds3505', 'cherry_dc', translator={
    'DC': 724050,
}).set(stage='Peak Bloom', cultivar='Yoshino')

years = (1990, 2000)

from pheno.estimation import GrowingDegree, AlternatingModel, SigmoidFunc, SequentialModel, ParallelModel, ThermalPeriod

gd = GrowingDegree(ds)
gd.calibrate(years)
gd.observes(years)
gd.estimates(years)

am = AlternatingModel(ds)
am.calibrate(years)

sf = SigmoidFunc(ds)
sf.calibrate(years)

sm = SequentialModel(ds)
sm.calibrate(years)

pm = ParallelModel(ds)
pm.calibrate(years)

tp = ThermalPeriod(ds)
tp.calibrate(years)
