import os

class Output(object):
    def __init__(self, basepath='./output', timestamp='current'):
        self.basepath = os.path.abspath(os.path.expanduser(basepath))
        self.timestamp = timestamp

    def path(self, kind, timestamp=None, makedirs=False):
        if timestamp is None:
            timestamp = self.timestamp
        p = os.path.join(self.basepath, timestamp, kind)
        if makedirs:
            os.makedirs(p, exist_ok=True)
        return p

    def filename(self, kind, basename, ext, timestamp=None, makedirs=True):
        p = self.path(kind, timestamp, makedirs)
        return os.path.join(p, '{}.{}'.format(basename, ext))

output = Output()
