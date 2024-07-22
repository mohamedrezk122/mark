import yaml
from tinydb.storages import Storage


class YAMLStorage(Storage):
    """Custom YAML storage layout for tinydb"""

    def __init__(self, filename):
        self.filename = filename

    def read(self):
        with open(self.filename, "r") as handle:
            try:
                data = yaml.safe_load(handle.read())
                return data
            except yaml.YAMLError:
                return None

    def write(self, data):
        with open(self.filename, "w+") as handle:
            yaml.dump(dict(data), handle)

    def close(self):
        pass
