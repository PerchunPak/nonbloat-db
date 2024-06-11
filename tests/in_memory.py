import typing as t

import pytest

from nbdb.storage import Storage


@pytest.fixture
async def storage() -> Storage:
    return await Storage.init()


@pytest.mark.parametrize("value", ("abc", 123123, {"hello": "world"}))
@pytest.mark.parametrize("value2", ("abc", 123123, {"hello": "world"}))
async def test_storage_in_memory(storage: Storage, value: t.Any, value2: t.Any) -> None:  # type: ignore[misc] # any
    await storage.set("abc", value)
    assert await storage.get("abc") == value

    await storage.set("akefoekof", value2)
    assert await storage.get("akefoekof") == value2
