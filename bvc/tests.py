"""Tests for Buildout version checker"""
from unittest import TestCase
from unittest import TestSuite
from unittest import TestLoader

from bvc import VersionsChecker
from bvc import VersionsConfigParser

VersionsChecker
VersionsConfigParser


class VersionsCheckerTestCase(TestCase):
    pass


class VersionsConfigParserTestCase(TestCase):
    pass


class CommandLineTestCase(TestCase):
    pass


loader = TestLoader()

test_suite = TestSuite([
    loader.loadTestsFromTestCase(VersionsCheckerTestCase),
    loader.loadTestsFromTestCase(VersionsConfigParserTestCase),
    loader.loadTestsFromTestCase(CommandLineTestCase)
    ]
)
