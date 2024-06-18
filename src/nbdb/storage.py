from __future__ import annotations

import asyncio
import json
import logging
import typing as t
from pathlib import Path

import aiofile
import typing_extensions as te

logger = logging.getLogger(__name__)

SERIALIZABLE_TYPE: te.TypeAlias = "str | int | dict | None"  # type: ignore[type-arg]
INTERNAL_DATA_TYPE: te.TypeAlias = t.Dict[str, SERIALIZABLE_TYPE]


class Storage:
    def __init__(self, path: Path | str) -> None:
        self._data: INTERNAL_DATA_TYPE = {}
        self._path = Path(path)
        self._tempfile = Path(str(self._path) + ".temp")
        # Append Only File, see https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
        self._aof_path = Path(str(self._path) + ".log.temp")

    @classmethod
    async def init(cls, path: Path | str) -> te.Self:
        instance = cls(path)
        await instance._read()
        return instance

    async def _read(self) -> None:
        path = self._path
        if self._tempfile.exists():
            logger.warning("Found tempfile with database, using it. Database file may be damaged")
            path = self._tempfile

        if path.exists():
            async with aiofile.async_open(path, "r") as f:
                self._data = json.loads(await f.read())
        else:
            self._data = {}

        if self._aof_path.exists():
            async with aiofile.AIOFile(self._aof_path, "r") as aof:
                async for line in aiofile.LineReader(aof):
                    for key, value in json.loads(line).items():
                        await self.set(key, value, _replay=True)

    async def _write(self) -> None:
        if self._path.exists():
            self._path.rename(self._tempfile)

        async with aiofile.async_open(self._path, "w") as f:
            await f.write(json.dumps(self._data))

        if self._aof_path.exists():
            self._aof_path.unlink()
        if self._tempfile.exists():
            self._tempfile.unlink()

    async def _append_command(self, key: str, value: SERIALIZABLE_TYPE) -> None:
        async with aiofile.async_open(self._aof_path, "a") as f:
            await f.write(json.dumps({key: value}))

    async def set(self, key: str, value: SERIALIZABLE_TYPE, _replay: bool = False) -> None:
        task = None
        if not _replay:
            task = asyncio.create_task(self._append_command(key, value))

        if value is None:
            del self._data[key]
            return

        self._data[key] = value

        if task is not None:
            await asyncio.gather(task)

    async def get(self, key: str) -> SERIALIZABLE_TYPE:
        return self._data[key]
