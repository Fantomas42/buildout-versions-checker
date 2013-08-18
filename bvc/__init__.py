"""Buildout version checker"""
import futures

import sys
import logging
import xmlrpclib
from optparse import OptionParser
from ConfigParser import NoSectionError
from ConfigParser import RawConfigParser
from distutils.version import LooseVersion

logger = logging.getLogger(__name__)


class VersionsChecker(object):

    def __init__(self, source):
        self.source = source
        config = RawConfigParser()
        config.read(self.source)
        self.versions = config.items('versions')
        logger.info('- %d packages need to be checked for updates.' %
                      len(self.versions))

    def find_latest_version(self, package, current_version):
        logger.debug('> Fetching latest datas for %s...' % package)
        package = package.lower()
        max_version = current_version
        client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
        results = client.search({'name': package})
        for result in results:
            if result['name'].lower() == package:
                if LooseVersion(result['version']) > LooseVersion(max_version):
                    max_version = result['version']
        logger.debug('>> Last version of %s is %s' % (package, max_version))
        return (package, max_version)

    def start(self):
        results = []
        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            tasks = [executor.submit(self.find_latest_version, *version)
                     for version in self.versions]
            for task in futures.as_completed(tasks):
                results.append(task.result())
        self.results = dict(results)

        updates = []
        for package, current_version in self.versions:
            if self.results[package] > current_version:
                updates.append((package, self.results[package]))
        self.updates = updates
        logger.info('- %d updates founds.' % len(updates))


def cmdline():
    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option(
        '-s', '--source', dest='source', type='string',
        help='The versions file used by Buildout',
        default='versions.cfg')
    parser.add_option(
        '-v', action='count', dest='verbosity',
        help='Increase verbosity (specify multiple times for more)')
    (options, args) = parser.parse_args()

    verbosity = options.verbosity
    if verbosity:
        console = logging.StreamHandler(sys.stdout)
        logger.addHandler(console)
        logger.setLevel(verbosity >= 2 and
                        logging.DEBUG or logging.INFO)

    try:
        versions_checker = VersionsChecker(options.source)
    except NoSectionError:
        sys.exit('Versions are not found in %s.' % options.source)

    versions_checker.start()

    for package, version in versions_checker.updates:
        print('%s= %s' % (package.ljust(24), version))

    sys.exit(0)


if __name__ == '__main__':
    cmdline()
