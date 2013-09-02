"""Tests for Buildout version checker"""
from tempfile import NamedTemporaryFile

from unittest import TestCase
from unittest import TestSuite
from unittest import TestLoader

from bvc import VersionsChecker
from bvc import VersionsConfigParser


class LazyVersionsChecker(VersionsChecker):
    """
    VersionsChecker who does nothing at the initialisation
    excepting recording the arguments.
    """
    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)


class VersionsCheckerTestCase(TestCase):

    def test_parse_versions(self):
        config_file = NamedTemporaryFile()
        config_file.write('[sections]\nKey=Value\n')
        config_file.seek(0)
        checker = LazyVersionsChecker()
        self.assertEquals(checker.parse_versions(config_file.name),
                          [])
        config_file.seek(0)
        config_file.write('[VERSIONS]\negg=0.1\nEgg = 0.2')
        config_file.seek(0)
        self.assertEquals(checker.parse_versions(config_file.name),
                          [])
        config_file.seek(0)
        config_file.write('[versions]\negg=0.1\nEgg = 0.2')
        config_file.seek(0)
        self.assertEquals(checker.parse_versions(config_file.name),
                          [('egg', '0.1'), ('Egg', '0.2')])
        config_file.close()


class VersionsConfigParserTestCase(TestCase):

    def test_parse_case_insensitive(self):
        config_file = NamedTemporaryFile()
        config_file.write('[Section]\nKEY=VALUE\nKey=Value\n')
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.readfp(config_file)
        self.assertEquals(config_parser.sections(), ['Section'])
        self.assertEquals(config_parser.options('Section'), ['KEY', 'Key'])
        config_file.close()

    def test_write_section(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section')
        config_parser.set('Section', 'Option', 'Value')
        config_parser.set('Section', 'Option-void', None)
        config_parser.set('Section', 'Option-multiline', 'Value1\nValue2')
        config_parser.write_section(config_file, 'Section')
        config_file.seek(0)
        self.assertEquals(
            ''.join(config_file.readlines()),
            '[Section]\n'
            'Option                  = Value\n'
            'Option-void             = \n'
            'Option-multiline        = Value1\n'
            '                          Value2\n')
        config_file.close()

    def test_write_section_custom_indentation(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.indentation = 12
        config_parser.add_section('Section')
        config_parser.set('Section', 'Option', 'Value')
        config_parser.set('Section', 'Option-void', None)
        config_parser.set('Section', 'Option-multiline', 'Value1\nValue2')
        config_parser.write_section(config_file, 'Section')
        config_file.seek(0)
        self.assertEquals(
            ''.join(config_file.readlines()),
            '[Section]\n'
            'Option      = Value\n'
            'Option-void = \n'
            'Option-multiline= Value1\n'
            '              Value2\n')
        config_file.close()

    def test_write(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section 1')
        config_parser.add_section('Section 2')
        config_parser.set('Section 1', 'Option', 'Value')
        config_parser.set('Section 1', 'Option-void', None)
        config_parser.set('Section 2', 'Option-multiline', 'Value1\nValue2')
        config_parser.write(config_file.name)
        config_file.seek(0)
        self.assertEquals(
            ''.join(config_file.readlines()),
            '[Section 1]\n'
            'Option                  = Value\n'
            'Option-void             = \n'
            '\n'
            '[Section 2]\n'
            'Option-multiline        = Value1\n'
            '                          Value2\n')
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
