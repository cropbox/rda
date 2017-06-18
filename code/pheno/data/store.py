from . import path

import pandas as pd

class AbstractStore(object):
    def __init__(self, pather=None):
        self.setup(pather)

    def setup(self, pather=None):
        if pather is None:
            pather = path.input
        self.pather = pather
        return self

    def _filename(self, kind, basename, ext):
        return self.pather.filename('df/{}'.format(kind), basename, ext)

    def _outfilename(self, kind, basename, ext):
        return self.pather.outfilename('df/{}'.format(kind), basename, ext)

    def read(self, kind, basename):
        raise NotImplementedError

    def write(self, df, kind, basename):
        raise NotImplementedError

class HDF5Store(AbstractStore):
    def read(self, kind, basename):
        return pd.read_hdf(self._filename(kind, basename, 'h5'), key=basename)

    def write(self, df, kind, basename):
        df.to_hdf(self._outfilename(kind, basename, 'h5'), key=basename, format='table', mode='w', complib='zlib')
        return df

class PickleStore(AbstractStore):
    def read(self, kind, basename):
        return pd.read_pickle(self._filename(kind, basename, 'pkl'))

    def write(self, df, kind, basename):
        df.to_pickle(self._outfilename(kind, basename, 'pkl'))
        return df

Store = HDF5Store
