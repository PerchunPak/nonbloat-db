import json
import logging
import typing as t
from pathlib import Path

import typing_extensions as te

logger = logging.getLogger(__name__)

SERIALIZABLE_TYPE: te.TypeAlias = "str | int | dict | None"
INTERNAL_DATA_TYPE: te.TypeAlias = t.Dict[str, SERIALIZABLE_TYPE]


class Storage:
    def __init__(self, path: Path | str) -> None:
        self._data: INTERNAL_DATA_TYPE = {}
        self._path = Path(path)
        self._tempfile = Path(str(self._path) + ".temp")

    @classmethod
    async def init(cls, path: Path | str) -> te.Self:
        instance = cls(path)
        await instance._read()
        return instance

    async def _read(self) -> None:
        if not self._path.exists():
            self._data = {}
            return

        path = self._path
        if self._tempfile.exists():
            logger.warning("Found tempfile with database, using it. Database file may be damaged")
            path = self._tempfile

        with path.open("r") as f:
            self._data = json.load(f)

    async def _write(self) -> None:
        self._path.replace(self._tempfile)

        with self._path.open("w") as f:
            json.dump(self._data, f)

        self._tempfile.unlink()

    async def set(self, key: str, value: SERIALIZABLE_TYPE) -> None:
        if value is None:
            del self._data[key]
            return

        self._data[key] = value

    async def get(self, key: str) -> SERIALIZABLE_TYPE:
        return self._data[key]
