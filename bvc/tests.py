"""Tests for Buildout version checker"""
from collections import OrderedDict
from tempfile import NamedTemporaryFile

from unittest import TestCase
from unittest import TestSuite
from unittest import TestLoader

import bvc
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


class PypiServerProxy(object):
    """
    Fake Pypi proxy server.
    """
    results = {
        'egg': [
            {'name': 'Egg', 'version': '0.2'},
            {'name': 'EGG', 'version': '0.3'},
            {'name': 'eggtractor', 'version': '0.42'}
        ]
    }

    def __init__(*ka, **kw):
        pass

    def search(self, query_dict):
        try:
            return self.results[query_dict['name']]
        except KeyError:
            pass
        return []


class VersionsCheckerTestCase(TestCase):

    def setUp(self):
        self.checker = LazyVersionsChecker()
        self.stub_server_proxy()

    def tearDown(self):
        self.unstub_server_proxy()

    def stub_server_proxy(self):
        """
        Replace the ServerProxy class used in bvc.
        """
        self.original_server_proxy = bvc.ServerProxy
        bvc.ServerProxy = PypiServerProxy

    def unstub_server_proxy(self):
        """
        Restaure the original ServerProxy class.
        """
        bvc.ServerProxy = self.original_server_proxy

    def test_parse_versions(self):
        config_file = NamedTemporaryFile()
        config_file.write('[sections]\nKey=Value\n')
        config_file.seek(0)
        self.assertEquals(self.checker.parse_versions(config_file.name),
                          [])
        config_file.seek(0)
        config_file.write('[VERSIONS]\negg=0.1\nEgg = 0.2')
        config_file.seek(0)
        self.assertEquals(self.checker.parse_versions(config_file.name),
                          [])
        config_file.seek(0)
        config_file.write('[versions]\negg=0.1\nEgg = 0.2')
        config_file.seek(0)
        self.assertEquals(self.checker.parse_versions(config_file.name),
                          [('egg', '0.1'), ('Egg', '0.2')])
        config_file.close()

    def test_include_exclude_versions(self):
        source_versions = OrderedDict([('egg', '0.1'), ('Egg', '0.2')])
        self.assertEquals(self.checker.include_exclude_versions(
            source_versions), source_versions)
        results = source_versions.copy()
        results['Django'] = '0.0.0'
        self.assertEquals(
            self.checker.include_exclude_versions(
                source_versions, includes=['Django', 'egg']),
            results)
        source_versions['Django'] = '1.5.1'
        source_versions['pytz'] = '2013b'
        results = OrderedDict([('pytz', '2013b')])
        self.assertEquals(
            self.checker.include_exclude_versions(
                source_versions, excludes=['Django', 'egg']),
            results)
        self.assertEquals(
            self.checker.include_exclude_versions(
                source_versions,
                includes=['Django', 'egg'],
                excludes=['Django', 'egg']),
            results)
        results['zc.buildout'] = '0.0.0'
        self.assertEquals(
            self.checker.include_exclude_versions(
                source_versions,
                includes=['zc.buildout'],
                excludes=['Django', 'egg']),
            results)

    def test_fetch_last_versions(self):
        self.assertEquals(
            self.checker.fetch_last_versions(
                ['egg', 'UnknowEgg'], 1, 'service_url'),
            [('egg', '0.3'), ('UnknowEgg', '0.0.0')])
        results = self.checker.fetch_last_versions(
            ['egg', 'UnknowEgg'], 2, 'service_url')
        self.assertEquals(
            dict(results),
            dict([('egg', '0.3'), ('UnknowEgg', '0.0.0')]))

    def test_fetch_last_version(self):
        self.assertEquals(
            self.checker.fetch_last_version('UnknowEgg', 'service_url'),
            ('UnknowEgg', '0.0.0')
        )
        self.assertEquals(
            self.checker.fetch_last_version('egg', 'service_url'),
            ('egg', '0.3')
        )

    def test_find_updates(self):
        versions = OrderedDict([('egg', '1.5.1'), ('Egg', '0.0.0')])
        last_versions = OrderedDict([('egg', '1.5.1'), ('Egg', '1.0')])
        self.assertEquals(self.checker.find_updates(
            versions, last_versions), [('Egg', '1.0')])


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
