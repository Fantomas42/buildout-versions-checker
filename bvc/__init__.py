"""Buildout Versions Checker"""
from bvc.checker import VersionsChecker
from bvc.configparser import VersionsConfigParser
from bvc.scripts.check_buildout_updates import cmdline

__all__ = [
    VersionsChecker.__name__,
    VersionsConfigParser.__name__
]

if __name__ == '__main__':
    cmdline()  # pragma: no cover
