"""Version checker for Buildout Versions Checker"""
import futures

import os
import json
import socket

from collections import OrderedDict
try:
    from urllib2 import urlopen
    from urllib2 import URLError
    from ConfigParser import NoSectionError
except ImportError:  # Python 3
    from urllib.error import URLError
    from urllib.request import urlopen
    from configparser import NoSectionError

from packaging.specifiers import SpecifierSet
from packaging.version import parse as parse_version

from bvc.logger import logger
from bvc.configparser import VersionsConfigParser


class VersionsChecker(object):
    """
    Checks updates of packages from a config file on Pypi.
    """
    default_version = '0.0.0'

    def __init__(self, source,
                 specifiers={}, allow_pre_releases=False,
                 includes=[], excludes=[],
                 service_url='http://pypi.python.org/pypi',
                 timeout=10, threads=10):
        """
        Parses a config file containing pinned versions
        of eggs and check available updates.
        """
        self.source = source
        self.includes = includes
        self.excludes = excludes
        self.specifiers = specifiers
        self.allow_pre_releases = allow_pre_releases
        self.timeout = timeout
        self.threads = threads
        self.service_url = service_url

        self.source_versions = OrderedDict(
            self.parse_versions(self.source))
        self.versions = self.include_exclude_versions(
            self.source_versions, self.includes, self.excludes)
        self.package_specifiers = self.build_specifiers(
            self.versions.keys(), self.specifiers)
        self.last_versions = OrderedDict(
            self.fetch_last_versions(self.package_specifiers,
                                     self.allow_pre_releases,
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

    def build_specifiers(self, packages, source_specifiers):
        """
        Builds a list of tuple (package, version specifier)
        """
        specifiers = []
        source_specifiers = dict((k.lower(), v) for k, v in
                                 source_specifiers.items())
        for package in packages:
            specifier = source_specifiers.get(package.lower(), '')
            specifiers.append((package, specifier))
        return specifiers

    def fetch_last_versions(self, packages, allow_pre_releases,
                            service_url, timeout, threads):
        """
        Fetch the latest versions of a list of packages with specifiers,
        in a threaded manner or not.
        """
        versions = []
        if threads > 1:
            with futures.ThreadPoolExecutor(
                    max_workers=threads) as executor:
                tasks = [executor.submit(self.fetch_last_version,
                                         package, allow_pre_releases,
                                         service_url, timeout)
                         for package in packages]
                for task in futures.as_completed(tasks):
                    versions.append(task.result())
        else:
            for package in packages:
                versions.append(self.fetch_last_version(
                    package, allow_pre_releases, service_url, timeout))
        return versions

    def fetch_last_version(self, package, allow_pre_releases,
                           service_url, timeout):
        """
        Fetch the last version of a package on Pypi.
        """
        package, specifier = package
        specifier = SpecifierSet(specifier, allow_pre_releases)
        max_version = parse_version(self.default_version)
        logger.info('> Fetching latest datas for %s...' % package)
        package_json_url = '%s/%s/json' % (service_url, package)
        socket.setdefaulttimeout(timeout)
        try:
            content = urlopen(package_json_url).read()
        except URLError as error:
            content = '{"releases": []}'
            logger.debug('!> %s %s' % (package_json_url, error.reason))
        results = json.loads(content)
        socket.setdefaulttimeout(None)
        for version in specifier.filter(results['releases']):
            version = parse_version(version)
            if version > max_version:
                max_version = version
        logger.debug('-> Last version of %s%s is %s.' % (
            package, specifier, max_version))
        return (package, str(max_version))

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


class UnusedVersionsChecker(VersionsChecker):
    """
    Checks unused eggs in a config file.
    """

    def __init__(self, source, egg_directory, excludes=[]):
        """
        Parses a config file containing pinned versions
        of eggs and check their installation in the egg_directory.
        """
        self.source = source
        self.excludes = excludes
        self.egg_directory = egg_directory
        self.source_versions = OrderedDict(
            self.parse_versions(self.source))
        self.versions = self.include_exclude_versions(
            self.source_versions, excludes=self.excludes)
        self.used_versions = self.get_used_versions(self.egg_directory)
        self.unused = self.find_unused_versions(
            self.versions.keys(), self.used_versions)

    def get_used_versions(self, egg_directory):
        """
        Walk into the egg_directory to know the packages installed.
        """
        return [egg.split('-')[0] for egg in os.listdir(egg_directory)
                if egg.endswith('.egg')]

    def find_unused_versions(self, versions, used_versions):
        """
        Make the difference between the listed versions and
        the used versions.
        """
        unused = list(versions)
        used_version_lower = [x.lower() for x in used_versions]
        for version in versions:
            if version.lower().replace('-', '_') in used_version_lower:
                unused.remove(version)
        return unused
