"""Version checker for Buildout Versions Checker"""
import futures

import socket
from collections import OrderedDict
from distutils.version import LooseVersion
try:
    from xmlrpclib import ServerProxy
    from ConfigParser import NoSectionError
except ImportError:  # Python 3
    from xmlrpc.client import ServerProxy
    from configparser import NoSectionError

from bvc.logger import logger
from bvc.configparser import VersionsConfigParser


class VersionsChecker(object):
    """
    Checks updates of packages from a config file on Pypi.
    """
    default_version = '0.0.0'

    def __init__(self, source, includes=[], excludes=[],
                 service_url='http://pypi.python.org/pypi',
                 timeout=10, threads=10):
        """
        Parses a config file containing pinned versions
        of eggs and check available updates.
        """
        self.source = source
        self.includes = includes
        self.excludes = excludes
        self.timeout = timeout
        self.threads = threads
        self.service_url = service_url
        self.source_versions = OrderedDict(
            self.parse_versions(self.source))
        self.versions = self.include_exclude_versions(
            self.source_versions, self.includes, self.excludes)
        self.last_versions = OrderedDict(
            self.fetch_last_versions(self.versions.keys(),
                                     self.service_url,
                                     self.timeout,
                                     self.threads))
        self.updates = OrderedDict(self.find_updates(
            self.versions, self.last_versions))

    def parse_versions(self, source):
        """
        Parses the source file to return the packages
        with their current versions.
        """
        config = VersionsConfigParser()
        config.read(source)
        try:
            versions = config.items('versions')
        except NoSectionError:
            logger.debug("'versions' section not found in %s." % source)
            return []
        logger.info('- %d versions found in %s.' % (len(versions), source))
        return versions

    def include_exclude_versions(self, source_versions,
                                 includes=[], excludes=[]):
        """
        Includes and excludes packages to be checked in
        the default dict of packages with versions.
        """
        versions = source_versions.copy()
        packages_lower = [x.lower() for x in versions.keys()]
        for include in includes:
            if include.lower() not in packages_lower:
                versions[include] = self.default_version
        excludes_lower = [x.lower() for x in excludes]
        for package in versions.keys():
            if package.lower() in excludes_lower:
                del versions[package]
        logger.info('- %d packages need to be checked for updates.' %
                    len(versions))
        return versions

    def fetch_last_versions(self, packages, service_url, timeout, threads):
        """
        Fetch the latest versions of a list of packages,
        in a threaded manner or not.
        """
        versions = []
        if threads > 1:
            with futures.ThreadPoolExecutor(
                    max_workers=threads) as executor:
                tasks = [executor.submit(self.fetch_last_version,
                                         package, service_url, timeout)
                         for package in packages]
                for task in futures.as_completed(tasks):
                    versions.append(task.result())
        else:
            for package in packages:
                versions.append(self.fetch_last_version(
                    package, service_url, timeout))
        return versions

    def fetch_last_version(self, package, service_url, timeout):
        """
        Fetch the last version of a package on Pypi.
        """
        package_key = package.lower()
        max_version = self.default_version
        logger.info('> Fetching latest datas for %s...' % package)
        socket.setdefaulttimeout(timeout)
        client = ServerProxy(service_url)
        results = client.search({'name': package})
        socket.setdefaulttimeout(None)
        for result in results:
            if result['name'].lower() == package_key:
                if LooseVersion(result['version']) > LooseVersion(max_version):
                    max_version = result['version']
        logger.debug('-> Last version of %s is %s.' % (package, max_version))
        return (package, max_version)

    def find_updates(self, versions, last_versions):
        """
        Compare the current versions of the packages
        with the last versions to find updates.
        """
        updates = []
        for package, current_version in versions.items():
            last_version = last_versions[package]
            if last_version != current_version:
                logger.debug(
                    '=> %s current version (%s) and last '
                    'version (%s) are different.' %
                    (package, current_version, last_version))
                updates.append((package, last_version))
        logger.info('- %d package updates found.' % len(updates))
        return updates
