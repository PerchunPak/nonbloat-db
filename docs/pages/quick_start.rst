Quick start
===========

To start using this database, you need to initialize :class:`~nbdb.storage.Storage`
class first.


.. code:: python

  from nbdb.storage import Storage

  db = await Storage.init("data/db.json")

.. note::

  We only support async context, so you have to run all of the examples in
  async functions. This means, to run this code in REPL, it should look like:

  .. code:: python

    import asyncio
    from nbdb.storage import Storage


    async def main():
        db = await Storage.init("data/db.json")


    asyncio.run(main())

  Or just use ``python -m asyncio`` instead of just ``python``, or even better
  - `ipython <https://ipython.org/>`_ (just a better REPL).

  This is also why you need to call :func:`Storage.init
  <nbdb.storage.Storage.init>` instead of ``__init__``: Python doesn't allow
  ``__init__`` to be async, so we have to create another method for this
  purpose.

After we initialized our database, we can set and get data from the database:

.. code:: python

  await db.set("abc", 123)
  print(await db.get("abc"))  # prints 123

You can also write changes to disk manually, by default it is saved every
5 minutes (you can change this interval when initializing the database, see
``write_interval`` in :func:`~nbdb.storage.Storage.init` method):

.. code:: python

  await db.write()
  # data/db.json appeared!

See also :ref:`pages/design_choices:data integrity` to learn why you don't have to manually
call :func:`~nbdb.storage.Storage.write` ever!

You can also manually read data from the database file, for example if you
changed it manually, by calling :func:`Storage.read()
<nbdb.storage.Storage.read>`. Do note that this method will rewrite all the
data stored in memory, as well as if you won't call this method, all data that
is not in memory will be overwritten. Automatically, it is called only during
initialization.

.. code:: python

  await db.read()
