"""Command line for (re)indenting buildout files"""
import logging
import sys

from argparse import ArgumentParser

from six import string_types

from bvc.configparser import VersionsConfigParser
from bvc.logger import logger


def cmdline(argv=sys.argv[1:]):
    parser = ArgumentParser(
        description='(Re)indent buildout related files')
    parser.add_argument(
        'sources', nargs='*',
        help='The buildout files to (re)indent')
    format_group = parser.add_argument_group('Formatting')
    format_group.add_argument(
        '--indent', dest='indentation', type=int, default=-1,
        help='Spaces used when indenting "key = value" (default: auto)')
    format_group.add_argument(
        '--sorting', dest='sorting', default='',
        choices=['alpha', 'ascii', 'length'],
        help='Sorting algorithm used on the keys when writing source file '
        '(default: None)')
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

    if not options.sources:
        logger.warning('No files to (re)indent')
        sys.exit(0)

    for source in options.sources:
        config = VersionsConfigParser(
            indentation=options.indentation,
            sorting=options.sorting)
        config_readed = config.read(source)
        if config_readed:
            config.write(source)
            logger.warning('- %s (re)indented at %s spaces.',
                           source, config.indentation)
        else:
            logger.warning('- %s cannot be read.', source)

    sys.exit(0)
