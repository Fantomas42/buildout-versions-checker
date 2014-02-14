=========================
Buildout Versions Checker
=========================

|travis-develop| |coverage-develop|

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
  Pillow                          = 2.0.0
  pytz                            = 2012j
  South                           = 0.8.1
  django                          = 1.5
  django-tagging                  = 0.3.1

Now let's execute the ``check-buildout-updates`` script: ::

  $ ./check-buildout-updates
  [versions]
  Pillow                          = 2.1.0
  pytz                            = 2013b
  South                           = 0.8.2
  django                          = 1.5.2

You can now update the ``versions.cfg`` file accordingly to your needs.

Options
-------

::

  usage: check-buildout-updates [-h] [-s SOURCE] [-i INCLUDES] [-e EXCLUDES]
                                [-w] [--indent INDENTATION]
                                [--sorting {alpha,length}]
                                [--service-url SERVICE_URL] [--timeout TIMEOUT]
                                [-t THREADS] [-v] [-q]

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
    --indent INDENTATION  Spaces used when indenting "key = value" (default: 32)
    --sorting {alpha,length}
                          Sorting algorithm used on the keys when writing source
                          file (default: None)
    --service-url SERVICE_URL
                          The service to use for checking the packages (default:
                          http://pypi.python.org/pypi)
    --timeout TIMEOUT     Timeout for each request (default: 10s)
    -t THREADS, --threads THREADS
                          Threads used for checking the versions in parallel
    -v                    Increase verbosity (specify multiple times for more)
    -q                    Decrease verbosity (specify multiple times for more)

Buildout integration
--------------------

You can easily integrate this script into your buildout script to
automaticly find and write the updates. ::

  [buildout]
  parts                   = evolution

  [evolution]
  recipe                  = zc.recipe.egg
  eggs                    = buildout-versions-checker
  scripts                 = check-buildout-updates=evolve
  arguments               = '-s versions.cfg -w'

With this part into your buildout, a new script named ``./bin/evolve`` will
be created. It will check for the available updates of the eggs listed in the
``versions`` section of the ``versions.cfg`` file, then write the updates found.

Extra
-----

Buildout-versions-checker provides an extra script named
``indent-buildout``, designed for just (re)indent your buildout files.
Because the buildout files are sometimes mixed with spaces and tabulations
which may affect viewing and editing. ::

  $ ./indent-buildout -s buildout.cfg

Python compatibility
--------------------

Buildout-versions-checker has been originally developed for Python 2.7, but
has been ported and tested for Python 3.2 and 3.3.

Requirements
------------

* six >= 1.4.1
* futures >= 2.1.4

.. _`zc.buildout`: http://www.buildout.org/
.. |travis-develop| image:: https://travis-ci.org/Fantomas42/buildout-versions-checker.png?branch=develop
   :alt: Build Status - develop branch
   :target: http://travis-ci.org/Fantomas42/buildout-versions-checker
.. |coverage-develop| image:: https://coveralls.io/repos/Fantomas42/buildout-versions-checker/badge.png?branch=develop
   :alt: Coverage of the code
   :target: https://coveralls.io/r/Fantomas42/buildout-versions-checker
