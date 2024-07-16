from __future__ import annotations

import asyncio
import json
import textwrap
import typing as t
from pathlib import Path

import pytest
import typing_extensions as te
from faker import Faker
from pytest_mock import MockerFixture

from nbdb.storage import Storage

STORAGE_FACTORY_RETURN_TYPE: te.TypeAlias = t.Callable[[], t.Awaitable[Storage]]


@pytest.fixture
async def storage_factory(tmp_path_factory: pytest.TempPathFactory, faker: Faker) -> STORAGE_FACTORY_RETURN_TYPE:
    async def factory(path: t.Optional[Path] = None, *args, **kwargs) -> Storage:
        if path is None:
            path = tmp_path_factory.mktemp("data") / (faker.pystr() + ".json")
        return await Storage.init(path, *args, **kwargs)

    return factory


@pytest.fixture
async def storage(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> Storage:
    return await storage_factory()


@pytest.mark.parametrize("value1_type", ("pystr", "pyint", "json"))
@pytest.mark.parametrize("value2_type", ("pystr", "pyint", "json"))
async def test_simple_storage(storage: Storage, faker: Faker, value1_type: str, value2_type: str) -> None:
    key1 = faker.pystr()
    key2 = faker.pystr()
    value1 = getattr(faker, value1_type)()
    value2 = getattr(faker, value2_type)()

    if value1_type == "json":
        value1 = json.loads(value1)
    if value2_type == "json":
        value2 = json.loads(value2)

    await storage.set(key1, value1)
    assert await storage.get(key1) == value1

    await storage.set(key2, value2)
    assert await storage.get(key2) == value2


@pytest.mark.parametrize("value_type", ("pystr", "pyint", "json"))
async def test_remove_item(storage: Storage, faker: Faker, value_type: str) -> None:
    key = faker.pystr()
    value = getattr(faker, value_type)()

    if value_type == "json":
        value = json.loads(value)

    await storage.set(key, value)
    await storage.set(key, None)

    with pytest.raises(KeyError):
        await storage.get(key)


async def test_storage_in_file(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> None:
    storage1 = await storage_factory()
    await storage1.set("abc", {"hello": "world"})
    await storage1.write()

    storage2 = await storage_factory(storage1._path)  # type: ignore[call-arg]
    assert storage2._data == {"abc": {"hello": "world"}}


async def test_failure_during_write(storage_factory: STORAGE_FACTORY_RETURN_TYPE, mocker: MockerFixture) -> None:
    storage1 = await storage_factory()
    mocker.patch.object(storage1, "_append_command")  # disable aof
    await storage1.set("abc", "abc")
    await storage1.write()

    await storage1.set("abc", {"hello": "world"})

    with mocker.patch.context_manager(json, "dumps", side_effect=IOError):
        with pytest.raises(IOError):
            await storage1.write()

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
    await storage.write()
    mocker.patch("json.dumps", side_effect=IOError)
    with pytest.raises(IOError):
        await storage.write()
    mocker.stopall()

    # create AOF file
    await storage.set("abc", 123)

    assert storage._path.exists()
    assert storage._tempfile.exists()
    assert storage._aof_path.exists()

    await storage.write()

    assert storage._path.exists()
    assert not storage._tempfile.exists()
    assert not storage._aof_path.exists()


async def test_write_in_background(
    storage_factory: STORAGE_FACTORY_RETURN_TYPE, faker: Faker, mocker: MockerFixture
) -> None:
    key, value = faker.pystr(), faker.pystr()
    storage = await storage_factory(write_interval=0.1)  # type: ignore[call-arg]
    mocker.patch.object(storage, "_append_command")  # disable AOF

    await storage.set(key, value)
    await asyncio.sleep(0.1)
    storage._write_loop_task.cancel()

    storage2 = await storage_factory(storage._path)  # type: ignore[call-arg]
    assert await storage2.get(key) == value


@pytest.mark.parametrize("t", [2, "\t", "aaaa"])
async def test_storage_indent(storage_factory: STORAGE_FACTORY_RETURN_TYPE, faker: Faker, t: str | int) -> None:
    key, value = faker.pystr(), faker.pystr()
    key2, value2 = faker.pystr(), faker.pystr()
    storage = await storage_factory(indent=t, write_interval=None)  # type: ignore[call-arg]

    if isinstance(t, int):
        t = " " * t

    await storage.set(key, value)
    await storage.set(key2, value2)
    await storage.write()

    with storage._path.open("r") as f:
        assert (
            f.read()
            == textwrap.dedent(
                f"""\
                    {'{'}
                    {t}"{key}": "{value}",
                    {t}"{key2}": "{value2}"
                    {'}'}
                """
            ).removesuffix("\n")
        )


async def test_storage_no_indent(storage_factory: STORAGE_FACTORY_RETURN_TYPE, faker: Faker) -> None:
    key, value = faker.pystr(), faker.pystr()
    key2, value2 = faker.pystr(), faker.pystr()
    storage = await storage_factory(indent=None, write_interval=None)  # type: ignore[call-arg]

    await storage.set(key, value)
    await storage.set(key2, value2)
    await storage.write()

    with storage._path.open("r") as f:
        assert f.read() == textwrap.dedent("{" + f'"{key}": "{value}", "{key2}": "{value2}"' + "}")
