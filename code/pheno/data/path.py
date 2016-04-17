import os

work_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
input_path = os.path.join(work_path, 'input')
output_path = os.path.join(work_path, 'output')

class Pather(object):
    def __init__(self, basepath, timestamp):
        self.setup(basepath, timestamp)

    def setup(self, basepath, timestamp):
        self.basepath = os.path.abspath(os.path.expanduser(basepath))
        self.timestamp = timestamp
        return self

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


class Input(Pather):
    def __init__(self, basepath=None):
        if basepath is None:
            basepath = input_path
        super(Input, self).__init__(basepath, timestamp='')
input = Input()


class Output(Pather):
    def __init__(self, basepath=None, timestamp=None):
        if basepath is None:
            basepath = output_path
        if timestamp is None:
            timestamp = 'current'
        super(Output, self).__init__(basepath, timestamp)
output = Output()
