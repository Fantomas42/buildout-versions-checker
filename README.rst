=========================
Buildout Versions Checker
=========================

Parses a `zc.buildout`_ version file, and checks if any updates are available.

If you use the practical convention to pin the versions of all the eggs
used in your buildout into a file, you will find this package useful for
checking if any newest version of the eggs are available on Pypi.

Here an example of a version file: ::

  $ cat versions.cfg
  [versions]
  Pillow				= 2.0.0
  pytz   				= 2012j
  South					= 0.8.1
  django				= 1.5
  django-tagging			= 0.3.1

Now let's execute the ``buildout_versions_check`` script: ::

  $ ./buildout_versions_check -v -s versions.cfg
  - 5 packages need to be checked for updates.
  - 4 updates founds.
  pillow                  = 2.1.0
  pytz                    = 2013b
  south                   = 0.8.2
  django                  = 1.5.2

You can now update the ``versions.cfg`` file accordingly to your needs.

.. _`zc.buildout`: http://www.buildout.org/
