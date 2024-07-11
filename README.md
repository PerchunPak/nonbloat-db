# nonbloat-db

[![Support Ukraine](https://badgen.net/badge/support/UKRAINE/?color=0057B8&labelColor=FFD700)](https://www.gov.uk/government/news/ukraine-what-you-can-do-to-help)

[![Build Status](https://github.com/PerchunPak/nonbloat-db/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/PerchunPak/nonbloat-db/actions?query=workflow%3Atest)
[![Documentation Build Status](https://readthedocs.org/projects/nonbloat-db/badge/?version=latest)](https://nonbloat-db.readthedocs.io/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python support versions badge (from pypi)](https://img.shields.io/pypi/pyversions/nonbloat-db)](https://www.python.org/downloads/)

Simple key-value database for my small projects!

The idea is to have a dead simple database, which doesn't require spinning up a
server (like Redis), is not underwhelming with features (like SQLite or SQL in
general), data inside can be easily manually reviewed and modified and it
doesn't corrupt (if you just dump JSON into file using `json.dump`, if the
program was forced to stop during write (e.g. because of power outage),
the data will be corrupted).

The purpose of this project is to serve as a database library for my small projects.
So obviously this solution doesn't scale to thousands of users, and it was
never intended to. Use right tool for right job.

Also, do note, that everything is async. There is no synchronous version,
because all of my projects are generally async. I maybe will add a synchronous
wrapper, but I don't promise.

## How does it work?

It is just a really simple key-value storage:

```python
import asyncio
from nbdb.storage import Storage


async def main():
    # you need to provide a path to database
    my_db = await Storage.init("data/db.json")
    await my_db.set("abc", 123)

    value = await my_db.get("abc")
    print(value)  # 123

    await my_db.write()


if __name__ == "__main__":
    asyncio.run(main())
```

> [!NOTE]
> Everything in this library is asynchronous, so you have to call it
> from async functions.

In the background, a lot of things are happening. For example, when you call
`.set`, the db writes the operation to special AOF (Append Only File; this is
what [Redis uses](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
to achieve data persistence).

And on every write, library renames `db.json` to `db.json.temp` and then writes
to `db.json` new data. This is done to not corrupt data in case of power outage
or force shutdown. If library during initial read finds a `.temp` file next to
database, it will output a warning and read from temp file.

## Installing

It is not yet published to PyPI, so good luck.

```bash
pip install nonbloat-db
```

## Installing for local developing

```bash
git clone https://github.com/PerchunPak/nonbloat-db.git
cd nonbloat-db
```

### Installing `poetry`

Next we need install `poetry` with [recommended way](https://python-poetry.org/docs/master/#installation).

If you use Linux, use command:

```bash
curl -sSL https://install.python-poetry.org | python -
```

If you use Windows, open PowerShell with admin privileges and use:

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### Installing dependencies

```bash
poetry install
```

### If something is not clear

You can always write me!

## Thanks

This project was generated with [python-template](https://github.com/PerchunPak/python-template).
