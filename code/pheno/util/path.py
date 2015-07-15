import os

class Path(object):
    def __init__(self, basepath, timestamp):
        self.basepath = os.path.abspath(os.path.expanduser(basepath))
        self.timestamp = timestamp

    def path(self, kind, timestamp=None, makedirs=False):
        if timestamp is None:
            timestamp = self.timestamp
        p = os.path.join(self.basepath, timestamp, kind)
        if makedirs:
            os.makedirs(p, exist_ok=True)
        return p

    def filename(self, kind, basename, ext, timestamp=None, makedirs=False):
        p = self.path(kind, timestamp, makedirs)
        return os.path.join(p, '{}.{}'.format(basename, ext))

    def outfilename(self, kind, basename, ext, timestamp=None, makedirs=True):
        return self.filename(kind, basename, ext, timestamp, makedirs)


class Input(Path):
    def __init__(self, basepath):
        super(Input, self).__init__(basepath, timestamp='')
input = Input(basepath='../input')


class Output(Path):
    def __init__(self, basepath, timestamp):
        super(Output, self).__init__(basepath, timestamp)
output = Output(basepath='../output', timestamp='current')
