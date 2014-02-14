"""Command line for Buildout Versions Checker"""
from six import string_types

import sys
import logging
from argparse import ArgumentParser

from bvc.logger import logger
from bvc.checker import VersionsChecker
from bvc.configparser import VersionsConfigParser


def cmdline(argv=sys.argv[1:]):
    parser = ArgumentParser(
        description='Check availables updates from a '
        'version section of a buildout script')
    parser.add_argument(
        '-s', '--source', dest='source', default='versions.cfg',
        help='The file where versions are pinned '
        '(default: versions.cfg)')
    parser.add_argument(
        '-i', '--include', action='append', dest='includes', default=[],
        help='Include package when checking updates '
        '(can be used multiple times)')
    parser.add_argument(
        '-e', '--exclude', action='append', dest='excludes', default=[],
        help='Exclude package when checking updates '
        '(can be used multiple times)')
    parser.add_argument(
        '-w', '--write', action='store_true', dest='write', default=False,
        help='Write the updates in the source file')
    parser.add_argument(
        '--indent', dest='indentation', type=int, default=32,
        help='Spaces used when indenting "key = value" (default: 32)')
    parser.add_argument(
        '--sorting', dest='sorting', default='', choices=['alpha', 'length'],
        help='Sorting algorithm used on the keys when writing source file '
        '(default: None)')
    parser.add_argument(
        '--service-url',  dest='service_url',
        default='http://pypi.python.org/pypi',
        help='The service to use for checking the packages '
        '(default: http://pypi.python.org/pypi)')
    parser.add_argument(
        '--timeout', dest='timeout', type=int, default=10,
        help='Timeout for each request (default: 10s)')
    parser.add_argument(
        '-t', '--threads', dest='threads', type=int, default=10,
        help='Threads used for checking the versions in parallel')
    parser.add_argument(
        '-v', action='count', dest='verbosity', default=1,
        help='Increase verbosity (specify multiple times for more)')
    parser.add_argument(
        '-q', action='count', dest='quietly', default=0,
        help='Decrease verbosity (specify multiple times for more)')

    if isinstance(argv, string_types):
        argv = argv.split()
    options = parser.parse_args(argv)

    verbose_logs = {0: 100,
                    1: logging.WARNING,
                    2: logging.INFO,
                    3: logging.DEBUG}
    verbosity = min(3, max(0, options.verbosity - options.quietly))
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(verbose_logs[verbosity])
    logger.addHandler(console)

    source = options.source
    try:
        checker = VersionsChecker(
            source, options.includes, options.excludes,
            options.service_url, options.timeout,
            options.threads)
    except Exception as e:
        sys.exit(str(e))

    if not checker.updates:
        sys.exit(0)

    logger.warning('[versions]')
    for package, version in checker.updates.items():
        logger.warning('%s= %s' % (
            package.ljust(options.indentation), version))

    if options.write:
        config = VersionsConfigParser()
        config.read(source)
        if not config.has_section('versions'):
            config.add_section('versions')
        for package, version in checker.updates.items():
            config.set('versions', package, version)

        config.write(source, options.indentation, options.sorting)
        logger.info('- %s updated.' % source)

    sys.exit(0)
