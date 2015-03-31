"""Command line for Buildout Versions Checker"""
from six import string_types

import sys
import copy
import logging
from argparse import Action
from argparse import ArgumentError
from argparse import ArgumentParser
from argparse import _ensure_value

from bvc.logger import logger
from bvc.checker import VersionsChecker
from bvc.configparser import VersionsConfigParser


class StoreSpecifiers(Action):

    def __call__(self, parser, namespace, values, option_string=None):
        items = copy.copy(_ensure_value(namespace, self.dest, {}))
        try:
            key, value = values.split(':')
        except ValueError:
            raise ArgumentError(self, 'key:value syntax not followed')
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ArgumentError(self, 'key or value are empty')
        items.update({key: value})
        setattr(namespace, self.dest, items)


def cmdline(argv=sys.argv[1:]):
    parser = ArgumentParser(
        description='Check availables updates from a '
        'version section of a buildout script')
    parser.add_argument(
        'source', default='versions.cfg', nargs='?',
        help='The file where versions are pinned '
        '(default: versions.cfg)')
    version_group = parser.add_argument_group('Allowed versions')
    version_group.add_argument(
        '--pre', action='store_true', dest='prereleases', default=False,
        help='Allow pre-releases and development versions '
        '(by default only stable versions are found)')
    version_group.add_argument(
        '-s', '--specifier', action=StoreSpecifiers,
        dest='specifiers', default={},
        help='Describe what versions of a package are acceptable. '
        'Example "package:>=1.0,!=1.3.4.*,< 2.0" '
        '(can be used multiple times)')
    filter_group = parser.add_argument_group('Filtering')
    filter_group.add_argument(
        '-i', '--include', action='append', dest='includes', default=[],
        help='Include package when checking updates '
        '(can be used multiple times)')
    filter_group.add_argument(
        '-e', '--exclude', action='append', dest='excludes', default=[],
        help='Exclude package when checking updates '
        '(can be used multiple times)')
    file_group = parser.add_argument_group('File')
    file_group.add_argument(
        '-w', '--write', action='store_true', dest='write', default=False,
        help='Write the updates in the source file')
    file_group.add_argument(
        '--indent', dest='indentation', type=int, default=32,
        help='Spaces used when indenting "key = value" (default: 32)')
    file_group.add_argument(
        '--sorting', dest='sorting', default='', choices=['alpha', 'length'],
        help='Sorting algorithm used on the keys when writing source file '
        '(default: None)')
    network_group = parser.add_argument_group('Network')
    network_group.add_argument(
        '--service-url',  dest='service_url',
        default='http://pypi.python.org/pypi',
        help='The service to use for checking the packages '
        '(default: http://pypi.python.org/pypi)')
    network_group.add_argument(
        '--timeout', dest='timeout', type=int, default=10,
        help='Timeout for each request (default: 10s)')
    network_group.add_argument(
        '-t', '--threads', dest='threads', type=int, default=10,
        help='Threads used for checking the versions in parallel')
    verbosity_group = parser.add_argument_group('Verbosity')
    verbosity_group.add_argument(
        '-v', action='count', dest='verbosity', default=1,
        help='Increase verbosity (specify multiple times for more)')
    verbosity_group.add_argument(
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
            source,
            options.specifiers, options.prereleases,
            options.includes, options.excludes,
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
