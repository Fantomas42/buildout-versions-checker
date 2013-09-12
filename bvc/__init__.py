"""Buildout Versions Checker"""
from bvc.cmdline import cmdline
from bvc.checker import VersionsChecker
from bvc.configparser import VersionsConfigParser

__all__ = [
    cmdline.__name__,
    VersionsChecker.__name__,
    VersionsConfigParser.__name__
]

if __name__ == '__main__':
    cmdline()  # pragma: no cover
