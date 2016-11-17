from .store import Store

import pandas as pd
import copy

class DataSet(object):
    def __init__(self, met_name, obs_name, name=None, translator=None, pather=None):
        self.translator = translator
        self.store = Store(pather)
        self.load(met_name, obs_name, name)
        self.reset()

    def __str__(self):
        return "met_station={}, obs_station={}, cultivar={}, stage={}, start_stage={}".format(
            self.met_station,
            self.obs_station,
            self.cultivar,
            self.stage,
            self.start_stage,
        )

    def load(self, met_name, obs_name, name=None):
        self.met_name = met_name
        self.metdf = self.store.read('met', met_name)

        self.obs_name = obs_name
        self.obsdf = self.store.read('obs', obs_name)

        self.name = obs_name if name is None else name

    def copy(self):
        return copy.copy(self)

    def translate(self, station):
        if self.translator is None:
            return station
        elif isinstance(self.translator, dict):
            return self.translator[station]
        else:
            return self.translator(station)

    # (re)set a specific dataset

    def reset(self):
        def pick(l):
            return l[0] if len(l) == 1 else None
        self.obs_station = pick(self.obs_stations())
        met_station = self.translate(self.obs_station)
        self.met_station = pick(self.met_stations()) if met_station is None else met_station
        self.cultivar = pick(self.cultivars())
        self.stage = pick(self.stages())
        self.start_stage = None
        return self

    def set(self, met_station=None, obs_station=None, cultivar=None, stage=None, start_stage=None):
        if obs_station in self.obs_stations():
            self.obs_station = obs_station
            self.met_station = self.translate(obs_station)
        if met_station in self.met_stations():
            self.met_station = met_station
        if cultivar in self.cultivars():
            self.cultivar = cultivar
        if stage in self.stages():
            self.stage = stage
        if start_stage in self.stages():
            self.start_stage = start_stage
        return self

    def ready(self):
        return all([
            self.obs_station in self.obs_stations(),
            self.met_station in self.met_stations(),
            self.cultivar in self.cultivars(),
            self.stage in self.stages(),
            self.start_stage in self.stages() if self.start_stage is not None else True,
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
            return self.obsdf.loc[station].loc[cultivar][stage]
        except:
            raise KeyError("invalid keys: station={}, cultivar={}, stage={}".format(station, cultivar, stage))

    def start_dates(self, station=None, cultivar=None, start_stage=None):
        station = self.obs_station if station is None else station
        cultivar = self.cultivar if cultivar is None else cultivar
        start_stage = self.start_stage if start_stage is None else start_stage
        if start_stage is None:
            return None
        try:
            return self.obsdf.loc[station].loc[cultivar][start_stage]
        except:
            raise KeyError("invalid keys: station={}, cultivar={}, start_stage={}".format(station, cultivar, start_stage))
