"""Tests for Buildout version checker"""
from tempfile import TemporaryFile

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

    def test_parse_case_insensitive(self):
        config_file = TemporaryFile()
        config_file.write('[Section]\nKEY=VALUE\nKey=Value\n')
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.readfp(config_file)
        self.assertEquals(config_parser.sections(), ['Section'])
        self.assertEquals(config_parser.options('Section'), ['KEY', 'Key'])
        config_file.close()

    def test_write_section(self):
        config_file = TemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section')
        config_parser.set('Section', 'Option', 'Value')
        config_parser.set('Section', 'Option-multiline', 'Value1\nValue2')
        config_parser.write_section(config_file, 'Section')
        config_file.seek(0)
        self.assertEquals(
            ''.join(config_file.readlines()),
            '[Section]\n'
            'Option                  = Value\n'
            'Option-multiline        = Value1\n'
            '                          Value2\n')
        config_file.close()

    def test_write_section_custom_indentation(self):
        config_file = TemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.indentation = 12
        config_parser.add_section('Section')
        config_parser.set('Section', 'Option', 'Value')
        config_parser.set('Section', 'Option-multiline', 'Value1\nValue2')
        config_parser.write_section(config_file, 'Section')
        config_file.seek(0)
        self.assertEquals(
            ''.join(config_file.readlines()),
            '[Section]\n'
            'Option      = Value\n'
            'Option-multiline= Value1\n'
            '              Value2\n')
        config_file.close()


class CommandLineTestCase(TestCase):
    pass


loader = TestLoader()

test_suite = TestSuite(
    [loader.loadTestsFromTestCase(VersionsCheckerTestCase),
     loader.loadTestsFromTestCase(VersionsConfigParserTestCase),
     loader.loadTestsFromTestCase(CommandLineTestCase)
     ]
)
