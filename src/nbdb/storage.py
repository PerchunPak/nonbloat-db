import json
import typing as t
from pathlib import Path

import typing_extensions as te

SERIALIZABLE_TYPE: te.TypeAlias = "str | int | dict | None"
INTERNAL_DATA_TYPE: te.TypeAlias = t.Dict[str, SERIALIZABLE_TYPE]


class Storage:
    def __init__(self, data: INTERNAL_DATA_TYPE, path: Path) -> None:
        self._data: INTERNAL_DATA_TYPE = {}
        self._path = path

    @classmethod
    async def init(cls, path: Path) -> te.Self:
        data = await cls._read(path)
        return cls(data, path)

    @staticmethod
    async def _read(path: Path) -> INTERNAL_DATA_TYPE:
        if not path.exists():
            return {}

        with path.open("r") as f:
            return json.load(f)  # type: ignore[no-any-return]

    async def _write(self) -> None:
        # TODO: tempfile
        with self._path.open("w") as f:
            json.dump(self._data, f)

    async def set(self, key: str, value: SERIALIZABLE_TYPE) -> None:
        if value is None:
            del self._data[key]
            return

        self._data[key] = value

    async def get(self, key: str) -> SERIALIZABLE_TYPE:
        return self._data[key]
