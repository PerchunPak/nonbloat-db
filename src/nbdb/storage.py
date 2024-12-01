from __future__ import annotations

import asyncio
import json
import logging
import typing as t
from pathlib import Path

import aiofile
import typing_extensions as te

if t.TYPE_CHECKING:
    import collections.abc as c

logger = logging.getLogger(__name__)

SERIALIZABLE_TYPE: te.TypeAlias = "str | int | JSON_TYPE | None"
"""Types that are JSON serializable."""
JSON_TYPE: te.TypeAlias = (
    "c.Mapping[str, SERIALIZABLE_TYPE] | c.Sequence[SERIALIZABLE_TYPE]"
)


@t.final
class Storage:
    """Core key-value store, that is responsible for correctly storing JSON and writing it to file."""

    def __init__(self, path: Path | str, *, indent: int | None) -> None:
        self._data: dict[str, SERIALIZABLE_TYPE] = {}
        self._path = Path(path)
        self._tempfile = Path(str(self._path) + ".temp")
        # Append Only File, see https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
        self._aof_path = Path(str(self._path) + ".log.temp")
        self._indent = indent

        self._write_loop_task: asyncio.Task[te.Never] = None  # pyright: ignore[reportAttributeAccessIssue]

    @classmethod
    async def init(
        cls,
        path: Path | str,
        *,
        write_interval: int | t.Literal[False] = 5 * 60,
        indent: int | None = 2,
    ) -> te.Self:
        """Python doesn't have async init methods, so we have to use this.

        Arguments:
            path:
                Path to database file. Do note that you should allocate entire
                folder to the database, because this library creates a few
                temp files near the db for technical reasons.
            write_interval:
                How often we should write to database in seconds? Set to ``False``
                to disable automatic writing at all.
            indent:
                If it is not ``None``, data in database file will be pretty
                printed with that indent level. Value is directly passed to
                :py:func:`json.dump`.
        """
        instance = cls(path, indent=indent)
        await instance.read()

        if write_interval:
            instance._write_loop_task = asyncio.create_task(
                instance._write_loop(write_interval)
            )

        return instance

    async def read(self) -> None:
        """Read content from the db file.

        This method is usually called only on initialization, but if you added
        some data to the file manually, you can call this method to sync
        in-memory state with what is written on disk.
        """
        path = self._path
        if self._tempfile.exists():
            logger.warning(
                "Found tempfile with database, using it. Database file may be damaged"
            )
            path = self._tempfile

        if path.exists():
            async with aiofile.async_open(path, "r") as f:
                content = t.cast(str, await f.read())
                if content != "":
                    self._data = json.loads(content)
                else:
                    self._data = {}
        else:
            self._data = {}

        if self._aof_path.exists():
            async with aiofile.AIOFile(self._aof_path, "r") as aof:
                async for line in aiofile.LineReader(aof):
                    if line == "\n":
                        # first line is always empty, because it is easier
                        # this way
                        continue

                    for key, value in t.cast(
                        dict[str, SERIALIZABLE_TYPE], json.loads(line)
                    ).items():
                        await self.set(key, value, _replay=True)

    async def write(self) -> None:
        """Save changes on disk.

        You can also manually call this method whenever you want.
        """
        if self._path.exists():
            _ = self._path.rename(self._tempfile)

        async with aiofile.async_open(self._path, "w") as f:
            _ = await f.write(
                json.dumps(self._data, indent=self._indent, ensure_ascii=False)
            )

        if self._aof_path.exists():
            self._aof_path.unlink()
        if self._tempfile.exists():
            self._tempfile.unlink()

    async def _write_loop(self, interval: int) -> te.Never:
        """Call :func:`.write` every N seconds.

        Arguments:
            interval: How long we wait between every write.
        """
        while True:
            try:
                await self.write()
            except Exception as exception:  # noqa: PERF203
                logger.exception("Error during write!", exc_info=exception)
            else:
                await asyncio.sleep(interval)

    async def _append_command(self, key: str, value: SERIALIZABLE_TYPE) -> None:
        """Handle AOF logic on every :func:`set`."""
        async with aiofile.async_open(self._aof_path, "a") as f:
            _ = await f.write("\n" + json.dumps({key: value}))

    async def set(
        self, key: str, value: SERIALIZABLE_TYPE, *, _replay: bool = False
    ) -> None:
        """Set a key to value.

        Arguments:
            _replay:
                If ``True``, we won't do AOF stuff. This is used when we replay
                operations from AOF.
        """
        task = None
        if not _replay:
            task = asyncio.create_task(self._append_command(key, value))

        if value is None:
            del self._data[key]
        else:
            self._data[key] = value

        if task is not None:
            _ = await asyncio.gather(task)

    async def get(self, key: str) -> SERIALIZABLE_TYPE:
        return self._data[key]
