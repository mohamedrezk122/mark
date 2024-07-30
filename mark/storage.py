import io
import os
import warnings

import orjson
import yaml
from tinydb.storages import Storage, touch


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


class FasterJSONStorage(Storage):
    """
    Faster JSON storage based on orjson parser.

    NOTE: The code of this class is the modified version of the
    JSONStorage provided by tinydb as orjson is not a drop replacement for builtin
    json module.
    """

    def __init__(
        self, path: str, create_dirs=False, encoding=None, access_mode="rb+", **kwargs
    ):

        super().__init__()
        self._mode = access_mode
        self.kwargs = kwargs
        if access_mode not in ("r", "rb", "r+", "rb+"):
            warnings.warn(
                "Using an `access_mode` other than 'r', 'rb', 'r+' "
                "or 'rb+' can cause data loss or corruption"
            )

        # Create the file if it doesn't exist and creating is allowed by the
        # access mode
        if any(
            [character in self._mode for character in ("+", "w", "a")]
        ):  # any of the writing modes
            touch(path, create_dirs=create_dirs)

        # Open the file for reading/writing
        self._handle = open(path, mode=self._mode, encoding=encoding)

    def close(self) -> None:
        self._handle.close()

    def read(self):
        # Get the file size by moving the cursor to the file end and reading
        # its location
        self._handle.seek(0, os.SEEK_END)
        size = self._handle.tell()

        if not size:
            # File is empty, so we return ``None`` so TinyDB can properly
            # initialize the database
            return None
        else:
            # Return the cursor to the beginning of the file
            self._handle.seek(0)

            # Load the JSON contents of the file
            return orjson.loads(self._handle.read())

    def write(self, data):
        # Move the cursor to the beginning of the file just in case
        self._handle.seek(0)

        # Serialize the database state using the user-provided arguments
        serialized = orjson.dumps(data, **self.kwargs)

        # Write the serialized data to the file
        try:
            self._handle.write(serialized)
        except io.UnsupportedOperation:
            raise IOError(
                'Cannot write to the database. Access mode is "{0}"'.format(self._mode)
            )

        # Ensure the file has been written
        self._handle.flush()
        os.fsync(self._handle.fileno())

        # Remove data that is behind the new cursor in case the file has
        # gotten shorter
        self._handle.truncate()
