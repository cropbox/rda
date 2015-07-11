from estimation import *
from . import export

import string

VALID_CHARS = frozenset("-_.() %s%s" % (string.ascii_letters, string.digits))
def _slugify(v):
    return ''.join(c for c in str(v) if c in VALID_CHARS)

def slugname(*args):
    return '_'.join([_slugify(k) for k in args])

DEFAULT_ESTIMATORS = [
    DegreeDay,
    ChillDay,
    BetaFunc,
    Dts,
]

RESULTS_PATH = 'results/current/'
FIGURES_PATH = 'figures/current/'
COEFFS_PATH = 'coeffs/current/'

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

        self.output = export.output if output is None else output

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
