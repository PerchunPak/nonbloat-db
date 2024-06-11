import typing as t

import pytest

from nbdb.storage import Storage


@pytest.fixture
async def storage() -> Storage:  # TODO: provide temp path
    return await Storage.init()


@pytest.mark.parametrize("value", ("abc", 123123, {"hello": "world"}))
@pytest.mark.parametrize("value2", ("abc", 123123, {"hello": "world"}))
async def test_simple_storage(storage: Storage, value: t.Any, value2: t.Any) -> None:  # type: ignore[misc] # any
    await storage.set("abc", value)
    assert await storage.get("abc") == value

    await storage.set("akefoekof", value2)
    assert await storage.get("akefoekof") == value2


async def test_storage_in_file(storage: Storage) -> None:
    await storage.set("abc", {"hello": "world"})
    await storage._write()
    assert await storage._read() == {"abc": {"hello": "world"}}


async def test_failure_during_write(storage: Storage) -> None:
    await storage.set("abc", "abc")
    await storage._write()

    await storage.set("abc", {"hello": "world"})
    await storage._write()  # TODO: simulate write failure

    storage2 = await Storage.init(storage._path)
    assert storage2.get("abc") == "abc"
