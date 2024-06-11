import typing as t

import typing_extensions as te

SERIALIZABLE_TYPE: te.TypeAlias = "str | int | dict | None"


class Storage:
    def __init__(self) -> None:
        self._data: t.Dict[str, SERIALIZABLE_TYPE] = {}

    @classmethod
    async def init(cls) -> te.Self:
        return cls()

    async def set(self, key: str, value: SERIALIZABLE_TYPE) -> None:
        if value is None:
            del self._data[key]
            return

        self._data[key] = value

    async def get(self, key: str) -> SERIALIZABLE_TYPE:
        return self._data[key]
