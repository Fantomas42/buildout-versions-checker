"""Buildout version checker"""
import futures

import sys
import logging
import xmlrpclib
from optparse import OptionParser
from collections import OrderedDict
from ConfigParser import NoSectionError
from ConfigParser import RawConfigParser
from distutils.version import LooseVersion

logger = logging.getLogger(__name__)


class VersionsConfigParser(RawConfigParser):
    optionxform = str


class VersionsChecker(object):
    max_worker = 10
    service_url = 'http://pypi.python.org/pypi'

    def __init__(self, source, threaded=True):
        self.source = source
        self.threaded = threaded
        self.versions = OrderedDict(
            self.parse_versions(self.source))
        self.last_versions = OrderedDict(
            self.fetch_last_versions(self.versions.keys(),
                                     self.threaded))
        self.updates = OrderedDict(self.find_updates(
            self.versions, self.last_versions))

    def parse_versions(self, source):
        config = VersionsConfigParser()
        config.read(source)
        try:
            versions = config.items('versions')
        except NoSectionError:
            raise Exception('Versions are not found in %s' % source)
        logger.info('- %d packages need to be checked for updates.' %
                    len(versions))
        return versions

    def fetch_last_versions(self, packages, threaded):
        versions = []
        if threaded:
            with futures.ThreadPoolExecutor(
                    max_workers=self.max_worker) as executor:
                tasks = [executor.submit(self.fetch_last_version, package)
                         for package in packages]
                for task in futures.as_completed(tasks):
                    versions.append(task.result())
        else:
            for package in packages:
                versions.append(self.fetch_last_version(package))

        return versions

    def fetch_last_version(self, package):
        package_key = package.lower()
        max_version = '0.0'
        logger.info('> Fetching latest datas for %s...' % package)
        client = xmlrpclib.ServerProxy(self.service_url)
        results = client.search({'name': package})
        for result in results:
            if result['name'].lower() == package_key:
                if LooseVersion(result['version']) > LooseVersion(max_version):
                    max_version = result['version']
        logger.debug('-> Last version of %s is %s.' % (package, max_version))
        return (package, max_version)

    def find_updates(self, versions, last_versions):
        updates = []
        for package, current_version in self.versions.items():
            last_version = last_versions[package]
            if last_version != current_version:
                logger.debug(
                    '=> %s current version (%s) and last '
                    'version (%s) are different.' %
                    (package, current_version, last_version))
                updates.append((package, last_version))
        logger.info('- %d package updates found.' % len(updates))
        return updates


def cmdline():
    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option(
        '-s', '--source', dest='source', type='string',
        help='The file where versions are pinned',
        default='versions.cfg')
    parser.add_option(
        '-w', '--write', action='store_true', dest='write',
        help='Write the updates in the source file',
        default=False)
    parser.add_option(
        '--no-threads', action='store_false', dest='threaded',
        help='Do not checks versions in parallel',
        default=True)
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

    source = options.source
    try:
        checker = VersionsChecker(source, options.threaded)
    except NoSectionError as e:
        sys.exit(e.message)

    if options.write and checker.updates:
        config = VersionsConfigParser()
        config.read(source)
        for package, version in checker.updates.items():
            config.set('versions', package, version)
        with open(source, 'wb') as fd:
            config.write(fd)
        logger.info('- %s updated.' % source)
    else:
        for package, version in checker.updates.items():
            print('%s= %s' % (package.ljust(24), version))

    sys.exit(0)


if __name__ == '__main__':
    cmdline()
