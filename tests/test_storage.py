from __future__ import annotations

import typing as t
from pathlib import Path

import pytest
import typing_extensions as te

from nbdb.storage import Storage

STORAGE_FACTORY_RETURN_TYPE: te.TypeAlias = t.Callable[[], t.Awaitable[Storage]]


@pytest.fixture
async def storage_factory(tmp_path_factory: pytest.TempPathFactory) -> STORAGE_FACTORY_RETURN_TYPE:
    async def factory(path: t.Optional[Path] = None) -> Storage:
        if path is None:
            path = tmp_path_factory.mktemp("data") / "database.json"
        return await Storage.init(path)

    return factory


@pytest.fixture
async def storage(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> Storage:
    return await storage_factory()


@pytest.mark.parametrize("value", ("abc", 123123, {"hello": "world"}))
@pytest.mark.parametrize("value2", ("abc", 123123, {"hello": "world"}))
async def test_simple_storage(storage: Storage, value: t.Any, value2: t.Any) -> None:  # type: ignore[misc] # any
    await storage.set("abc", value)
    assert await storage.get("abc") == value

    await storage.set("akefoekof", value2)
    assert await storage.get("akefoekof") == value2


async def test_storage_in_file(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> None:
    storage1 = await storage_factory()
    await storage1.set("abc", {"hello": "world"})
    await storage1._write()

    storage2 = await storage_factory(storage1._path)  # type: ignore[call-arg]
    assert storage2._data == {"abc": {"hello": "world"}}


async def test_failure_during_write(storage: Storage) -> None:
    await storage.set("abc", "abc")
    await storage._write()

    await storage.set("abc", {"hello": "world"})
    await storage._write()  # TODO: simulate write failure

    storage2 = await Storage.init(storage._path)
    assert await storage2.get("abc") == "abc"
