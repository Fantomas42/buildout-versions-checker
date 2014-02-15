"""Command line for (re)indenting buildout files"""
from six import string_types

import sys
import logging
from argparse import ArgumentParser

from bvc.logger import logger
from bvc.configparser import VersionsConfigParser


def cmdline(argv=sys.argv[1:]):
    parser = ArgumentParser(
        description='(Re)indent buildout related files')
    parser.add_argument(
        '-s', '--source', action='append', dest='sources',
        default=[], help='The buildout files to (re)indent')
    parser.add_argument(
        '--indent', dest='indentation', type=int, default=32,
        help='Spaces used when indenting "key = value" (default: 32)')
    parser.add_argument(
        '--sorting', dest='sorting', default='', choices=['alpha', 'length'],
        help='Sorting algorithm used on the keys when writing source file '
        '(default: None)')
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

    if not options.sources:
        logger.warning('No files to (re)indent')
        sys.exit(0)

    for source in options.sources:
        config = VersionsConfigParser()
        config_readed = config.read(source)
        if config_readed:
            config.write(source, options.indentation, options.sorting)
            logger.warning('- %s (re)indented at %s spaces.' % (
                source, options.indentation))
        else:
            logger.warning('- %s cannot be read.' % source)

    sys.exit(0)
