=========================
Buildout Versions Checker
=========================

Parses a `zc.buildout`_ file containing a ``versions`` section of the
pinned versions of the eggs, and checks if any updates are available.

Usage
-----

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

Now let's execute the ``check-buildout-updates`` script: ::

  $ ./check-buildout-updates -v -s versions.cfg
  - 5 packages need to be checked for updates.
  - 4 updates founds.
  Pillow                  = 2.1.0
  pytz                    = 2013b
  South                   = 0.8.2
  django                  = 1.5.2

You can now update the ``versions.cfg`` file accordingly to your needs.

Requirements
------------

* Python2 >= 2.7
* futures >= 2.1.4

.. _`zc.buildout`: http://www.buildout.org/
