from __future__ import annotations

import asyncio
import collections.abc as c
import json
import textwrap
import typing as t

import pytest
import typing_extensions as te

from nbdb.storage import SERIALIZABLE_TYPE, Storage

if t.TYPE_CHECKING:
    from pathlib import Path

    from faker import Faker
    from pytest_mock import MockerFixture

STORAGE_FACTORY_RETURN_TYPE: te.TypeAlias = t.Callable[[], c.Awaitable[Storage]]


@pytest.fixture
async def storage_factory(
    tmp_path_factory: pytest.TempPathFactory, faker: Faker
) -> STORAGE_FACTORY_RETURN_TYPE:
    async def factory(
        path: Path | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> Storage:
        if path is None:
            path = tmp_path_factory.mktemp("data") / (faker.pystr() + ".json")
        return await Storage.init(path, *args, **kwargs)

    return factory


@pytest.fixture
async def storage(storage_factory: STORAGE_FACTORY_RETURN_TYPE) -> Storage:
    return await storage_factory()


@pytest.mark.parametrize("value1_type", ["pystr", "pyint", "json"])
@pytest.mark.parametrize("value2_type", ["pystr", "pyint", "json"])
async def test_simple_storage(
    storage: Storage, faker: Faker, value1_type: str, value2_type: str
) -> None:
    key1 = faker.pystr()
    key2 = faker.pystr()
    value1 = t.cast(SERIALIZABLE_TYPE, getattr(faker, value1_type)())
    value2 = t.cast(SERIALIZABLE_TYPE, getattr(faker, value2_type)())

    if value1_type == "json":
        assert isinstance(value1, str)
        value1 = t.cast(SERIALIZABLE_TYPE, json.loads(value1))
    if value2_type == "json":
        assert isinstance(value2, str)
        value2 = t.cast(SERIALIZABLE_TYPE, json.loads(value2))

    await storage.set(key1, value1)
    assert await storage.get(key1) == value1

    await storage.set(key2, value2)
    assert await storage.get(key2) == value2


@pytest.mark.parametrize("value_type", ["pystr", "pyint", "json"])
async def test_remove_item(
    storage: Storage, faker: Faker, value_type: str
) -> None:
    key = faker.pystr()
    value = t.cast(SERIALIZABLE_TYPE, getattr(faker, value_type)())

    if value_type == "json":
        assert isinstance(value, str)
        value = t.cast(SERIALIZABLE_TYPE, json.loads(value))

    await storage.set(key, value)
    await storage.set(key, None)

    with pytest.raises(KeyError):
        _ = await storage.get(key)


async def test_storage_in_file(
    storage_factory: STORAGE_FACTORY_RETURN_TYPE,
) -> None:
    storage1 = await storage_factory()
    await storage1.set("abc", {"hello": "world"})
    await storage1.write()

    storage2 = await storage_factory(storage1._path)  # pyright: ignore[reportUnknownVariableType, reportCallIssue, reportPrivateUsage]
    assert storage2._data == {"abc": {"hello": "world"}}


async def test_failure_during_write(
    storage_factory: STORAGE_FACTORY_RETURN_TYPE, mocker: MockerFixture
) -> None:
    storage1 = await storage_factory()
    _ = mocker.patch.object(storage1, "_append_command")  # disable aof
    await storage1.set("abc", "abc")
    await storage1.write()

    await storage1.set("abc", {"hello": "world"})

    with (
        mocker.patch.context_manager(json, "dumps", side_effect=IOError),
        pytest.raises(IOError),  # noqa: PT011
    ):
        await storage1.write()

    storage2 = t.cast(Storage, await storage_factory(storage1._path))  # pyright: ignore[reportCallIssue, reportPrivateUsage]
    assert await storage2.get("abc") == "abc"


async def test_aof(
    storage_factory: STORAGE_FACTORY_RETURN_TYPE, faker: Faker
) -> None:
    key, value = faker.pystr(), faker.pystr()
    key2, value2 = faker.pystr(), faker.pystr()

    storage1 = t.cast(Storage, await storage_factory(write_interval=False))  # pyright: ignore[reportCallIssue]
    await storage1.set(key, value)
    await storage1.set(key2, value2)

    storage2 = t.cast(
        Storage,
        await storage_factory(storage1._path, write_interval=False),  # pyright: ignore[reportCallIssue, reportPrivateUsage]
    )
    assert await storage2.get(key) == value
    assert await storage2.get(key2) == value2


async def test_aof_failure(storage: Storage, mocker: MockerFixture) -> None:
    # disable aof
    _ = mocker.patch.object(storage, "_append_command", side_effect=IOError)

    with pytest.raises(IOError):  # noqa: PT011
        await storage.set("123", "abc")


async def test_write_deletes_tempfiles(
    storage: Storage, mocker: MockerFixture
) -> None:
    # create temp file by write failure
    await storage.write()
    _ = mocker.patch("json.dumps", side_effect=IOError)
    with pytest.raises(IOError):  # noqa: PT011
        await storage.write()
    mocker.stopall()

    # create AOF file
    await storage.set("abc", 123)

    assert storage._path.exists()  # pyright: ignore[reportPrivateUsage]
    assert storage._tempfile.exists()  # pyright: ignore[reportPrivateUsage]
    assert storage._aof_path.exists()  # pyright: ignore[reportPrivateUsage]

    await storage.write()

    assert storage._path.exists()  # pyright: ignore[reportPrivateUsage]
    assert not storage._tempfile.exists()  # pyright: ignore[reportPrivateUsage]
    assert not storage._aof_path.exists()  # pyright: ignore[reportPrivateUsage]


async def test_write_in_background(
    storage_factory: STORAGE_FACTORY_RETURN_TYPE,
    faker: Faker,
    mocker: MockerFixture,
) -> None:
    key, value = faker.pystr(), faker.pystr()
    storage = t.cast(Storage, await storage_factory(write_interval=0.1))  # pyright: ignore[reportCallIssue]
    _ = mocker.patch.object(storage, "_append_command")  # disable AOF

    await storage.set(key, value)
    await asyncio.sleep(0.1)
    _ = storage._write_loop_task.cancel()  # pyright: ignore[reportPrivateUsage]

    storage2 = t.cast(Storage, await storage_factory(storage._path))  # pyright: ignore[reportCallIssue, reportPrivateUsage]
    assert await storage2.get(key) == value


@pytest.mark.parametrize("v", [2, "\t", "aaaa"])
async def test_storage_indent(
    storage_factory: STORAGE_FACTORY_RETURN_TYPE, faker: Faker, v: str | int
) -> None:
    key, value = faker.pystr(), faker.pystr()
    key2, value2 = faker.pystr(), faker.pystr()
    storage = t.cast(
        Storage,
        await storage_factory(indent=v, write_interval=False),  # pyright: ignore[reportCallIssue]
    )

    if isinstance(v, int):
        v = " " * v

    await storage.set(key, value)
    await storage.set(key2, value2)
    await storage.write()

    with storage._path.open("r") as f:  # pyright: ignore[reportPrivateUsage]
        assert f.read() == textwrap.dedent(
            f"""\
                {'{'}
                {v}"{key}": "{value}",
                {v}"{key2}": "{value2}"
                {'}'}
            """
        ).removesuffix("\n")


async def test_storage_no_indent(
    storage_factory: STORAGE_FACTORY_RETURN_TYPE, faker: Faker
) -> None:
    key, value = faker.pystr(), faker.pystr()
    key2, value2 = faker.pystr(), faker.pystr()
    storage = t.cast(
        Storage,
        await storage_factory(indent=None, write_interval=False),  # pyright: ignore[reportCallIssue]
    )

    await storage.set(key, value)
    await storage.set(key2, value2)
    await storage.write()

    with storage._path.open("r") as f:  # pyright: ignore[reportPrivateUsage]
        assert f.read() == textwrap.dedent(
            "{" + f'"{key}": "{value}", "{key2}": "{value2}"' + "}"
        )
