from __future__ import annotations

import asyncio
import json
import typing as t
from pathlib import Path

import pytest
import typing_extensions as te
from pytest_mock import MockerFixture

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


async def test_failure_during_write(storage_factory: STORAGE_FACTORY_RETURN_TYPE, mocker: MockerFixture) -> None:
    storage1 = await storage_factory()
    await storage1.set("abc", "abc")
    await storage1._write()

    await storage1.set("abc", {"hello": "world"})

    with mocker.patch.context_manager(json, "dumps", side_effect=IOError):
        with pytest.raises(IOError):
            await storage1._write()
    assert len(storage1._background_tasks) == 0

    storage2 = await storage_factory(storage1._path)  # type: ignore[call-arg]
    assert await storage2.get("abc") == "abc"


async def test_aof(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> None:
    storage1 = await storage_factory()
    await storage1.set("abcabc", "123")
    await asyncio.gather(*storage1._background_tasks)

    storage2 = await storage_factory(storage1._path)  # type: ignore[call-arg]
    assert await storage2.get("abcabc") == "123"
