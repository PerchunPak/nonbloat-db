Design choices
==============

The goals of this project are simple:

* Be dead simple

  A user must not spin up a server to run the database (Redis, PostreSQL,
  MySQL), there must not be underwhelming amount of features (like in SQL), it
  must not be an overkill for 200 lines project, etc.

* Data inside can be easily reviewed and modified

  We store all data in JSON format, furthermore indents are added by default.
  Which means, that you will see this

  .. code:: json

    {
      "abc": 123,
      "a": {
        "b": {
          "c": "cool, i am readable"
        }
      }
    }

  instead of this

  .. code:: json

    {"abc":123,"a":{"b":{"c":"oh no i am unreadable!"}}}

  Of course this can be turned off in :func:`Storage.init()
  <nbdb.storage.Storage.init>` method by setting ``indent`` to ``None``.

* No data corruption

  I had to manually restore database from backups more than a dozen times when
  I had one small project with rapidly changing JSON database. As you can
  imagine, it was mildly annoying, especially because at that time there were
  constant energy outages in Ukraine (server was in Ukraine at that time)
  because of, you know, terroristic attacks during `the war
  <https://s.perchun.it/ukraine>`_.

  This is why I took great ideas of data integrity `from Redis <https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/>`_
  and implemented them for my small project.

Data integrity
--------------

I use two methods for ensuring that data is save whatever happens to the server:

1. Write database on disk every 5 minutes (interval can be tweaked in
   :func:`Storage.init() <nbdb.storage.Storage.init>`).

   Maybe you know, that if you interrupt Python process during write, it won't
   finish and will write only part of the data. This is because when you open
   a file in write mode, the file is deleted immediately and on its place you
   start to write your data.

   To overcome this, the library firstly moves old database to ``db.json.temp``
   file and then write to actual ``.json`` file. When the library finishes
   writing, it will remove temp file. If library is asked to read from database
   and sees a temporary file, it will read from the ``.temp`` and output
   a warning.

2. Append Only File.

   On every :func:`~nbdb.storage.Storage.set` you do, your actions are
   **appended** to file named ``db.json.log.temp`` and then if the library
   notices this file on read, it will replay actions from this file and delete
   it on next write.

This way we ensure that no data will be lost.
