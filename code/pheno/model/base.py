from ..data import path

from ..estimation.base import slugname
from ..estimation.gd import GrowingDegree
from ..estimation.cf import ChillingForce, ChillingForceDay
from ..estimation.beta import BetaFunc
from ..estimation.dts import StandardTemperature
from ..estimation.sigmoid import SigmoidFunc
from ..estimation.tp import ThermalPeriod
from ..estimation.spm import SequentialModel, ParallelModel
from ..estimation.am import AlternatingModel
from ..estimation.mean import Mean

DEFAULT_ESTIMATORS = [
    GrowingDegree,
    ChillingForce,
    BetaFunc,
    StandardTemperature,
    SigmoidFunc,
    ThermalPeriod,
    SequentialModel,
    ParallelModel,
    AlternatingModel,
    Mean,
]

class Model(object):
    def __init__(self, dataset,
                 calibrate_years, validate_years, export_years,
                 crossvalidate_n=1, ESTIMATORS=DEFAULT_ESTIMATORS,
                 output=None):
        self.dataset = dataset

        self.calibrate_years = calibrate_years
        self.validate_years = validate_years
        self.export_years = export_years

        self.crossvalidate_n = crossvalidate_n
        self.ESTIMATORS = ESTIMATORS

        self.output = path.output if output is None else output

        self.create()

    def create(self):
        raise NotImplementedError

    def export(self):
        raise NotImplementedError

    def _key_for_calibration(self):
        return slugname(
            self.dataset.name,
            self.dataset.cultivar,
            self.dataset.met_station,
            self.dataset.obs_station,
            self.calibrate_years,
            self.dataset.stage,
        )

    def _key_for_validation(self):
        return slugname(
            self.dataset.name,
            self.dataset.cultivar,
            self.dataset.met_station,
            self.dataset.obs_station,
            self.calibrate_years,
            self.validate_years,
            self.dataset.stage,
        )
