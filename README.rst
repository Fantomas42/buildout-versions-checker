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
  Pillow                  = 2.0.0
  pytz                    = 2012j
  South                   = 0.8.1
  django                  = 1.5
  django-tagging          = 0.3.1

Now let's execute the ``check-buildout-updates`` script: ::

  $ ./check-buildout-updates
  [versions]
  Pillow                  = 2.1.0
  pytz                    = 2013b
  South                   = 0.8.2
  django                  = 1.5.2

You can now update the ``versions.cfg`` file accordingly to your needs.

Options
-------

::

  usage: check-buildout-updates [-h] [-s SOURCE] [-i INCLUDES] [-e EXCLUDES]
                                [-w] [--indent INDENTATION] [--no-threads] [-v]

  Check availables updates from a version section of a buildout script

  optional arguments:
    -h, --help            show this help message and exit
    -s SOURCE, --source SOURCE
                          The file where versions are pinned (default:
                          versions.cfg)
    -i INCLUDES, --include INCLUDES
                          Include package when checking updates (can be used
                          multiple times)
    -e EXCLUDES, --exclude EXCLUDES
                          Exclude package when checking updates (can be used
                          multiple times)
    -w, --write           Write the updates in the source file
    --indent INDENTATION  Spaces used when indenting "key = value" (default: 24)
    --no-threads          Do not checks versions in parallel
    -v                    Increase verbosity (specify multiple times for more)

Requirements
------------

* Python2 >= 2.7
* futures >= 2.1.4

.. _`zc.buildout`: http://www.buildout.org/
