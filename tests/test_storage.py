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


async def test_remove_item(storage: Storage) -> None:  # type: ignore[misc] # any
    await storage.set("abc", "123")
    await storage.set("abc", None)

    with pytest.raises(KeyError):
        await storage.get("abc")


async def test_storage_in_file(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> None:
    storage1 = await storage_factory()
    await storage1.set("abc", {"hello": "world"})
    await storage1._write()

    storage2 = await storage_factory(storage1._path)  # type: ignore[call-arg]
    assert storage2._data == {"abc": {"hello": "world"}}


async def test_failure_during_write(storage_factory: STORAGE_FACTORY_RETURN_TYPE, mocker: MockerFixture) -> None:
    storage1 = await storage_factory()
    mocker.patch.object(storage1, "_append_command")  # disable aof
    await storage1.set("abc", "abc")
    await storage1._write()

    await storage1.set("abc", {"hello": "world"})

    with mocker.patch.context_manager(json, "dumps", side_effect=IOError):
        with pytest.raises(IOError):
            await storage1._write()

    storage2 = await storage_factory(storage1._path)  # type: ignore[call-arg]
    assert await storage2.get("abc") == "abc"


async def test_aof(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> None:
    storage1 = await storage_factory()
    await storage1.set("abcabc", "123")

    storage2 = await storage_factory(storage1._path)  # type: ignore[call-arg]
    assert await storage2.get("abcabc") == "123"


async def test_aof_failure(storage: Storage, mocker: MockerFixture) -> None:
    # disable aof
    mocker.patch.object(storage, "_append_command", side_effect=IOError)

    with pytest.raises(IOError):
        await storage.set("123", "abc")


async def test_write_deletes_tempfiles(storage: Storage, mocker: MockerFixture) -> None:
    # create temp file by write failure
    await storage._write()
    mocker.patch("json.dumps", side_effect=IOError)
    with pytest.raises(IOError):
        await storage._write()
    mocker.stopall()

    # create AOF file
    await storage.set("abc", 123)

    assert storage._path.exists()
    assert storage._tempfile.exists()
    assert storage._aof_path.exists()

    await storage._write()

    assert storage._path.exists()
    assert not storage._tempfile.exists()
    assert not storage._aof_path.exists()
