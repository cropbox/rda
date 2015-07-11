import pandas as pd
import copy

class DataSet(object):
    def __init__(self, met_name, obs_name, name=None, mapper=None):
        self.load(met_name, obs_name, name)
        self.setup(mapper)
        self.reset()

    def __str__(self):
        return "met_station={}, obs_station={}, cultivar={}, stage={}".format(
            self.met_station,
            self.obs_station,
            self.cultivar,
            self.stage
        )

    def load(self, met_name, obs_name, name=None):
        self.met_name = met_name
        met_filename = 'data/{}.pkl'.format(met_name)
        self.metdf = pd.read_pickle(met_filename)

        self.obs_name = obs_name
        obs_filename = 'data/{}.pkl'.format(obs_name)
        self.obsdf = pd.read_pickle(obs_filename)

        self.name = obs_name if name is None else name

    def setup(self, mapper):
        def create_dict_mapper(mapper):
            def f(x):
                try:
                    return mapper[x]
                except:
                    return None
            return f

        if mapper is None:
            self.mapper = lambda x: x
        elif type(mapper) is dict:
            self.mapper = create_dict_mapper(mapper)
        else:
            self.mapper = mapper

    def copy(self):
        return copy.copy(self)

    # (re)set a specific dataset

    def reset(self):
        def pick(l):
            return l[0] if len(l) == 1 else None
        self.obs_station = pick(self.obs_stations())
        met_station = self.mapper(self.obs_station)
        self.met_station = pick(self.met_stations()) if met_station is None else met_station
        self.cultivar = pick(self.cultivars())
        self.stage = pick(self.stages())
        return self

    def set(self, met_station=None, obs_station=None, cultivar=None, stage=None):
        if obs_station is not None:
            self.obs_station = obs_station
            self.met_station = self.mapper(obs_station)
        if met_station is not None:
            self.met_station = met_station
        if cultivar is not None:
            self.cultivar = cultivar
        if stage is not None:
            self.stage = stage
        return self

    def ready(self):
        return all([
            self.obs_station in self.obs_stations(),
            self.met_station in self.met_stations(),
            self.cultivar in self.cultivars(),
            self.stage in self.stages(),
        ])

    # return avaialble indices

    def met_stations(self):
        return self.metdf.index.levels[0].tolist()

    def obs_stations(self):
        return self.obsdf.index.levels[0].tolist()

    def cultivars(self):
        return self.obsdf.index.levels[1].tolist()

    def stages(self):
        return self.obsdf.columns.tolist()

    # return corresponding weather / observation to be used in the model

    def weather(self, station=None):
        station = self.met_station if station is None else station
        try:
            return self.metdf.loc[station]
        except:
            raise KeyError("invalid key: station={}".format(station))

    def observation(self, station=None, cultivar=None, stage=None):
        station = self.obs_station if station is None else station
        cultivar = self.cultivar if cultivar is None else cultivar
        stage = self.stage if stage is None else stage
        try:
            return self.obsdf.loc[station, cultivar][stage]
        except:
            raise KeyError("invalid keys: station={}, cultivar={}, stage={}".format(station, cultivar, stage))
