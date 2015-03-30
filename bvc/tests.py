"""Tests for Buildout version checker"""
import os
import sys
import json

from logging import Handler
from collections import OrderedDict
from tempfile import NamedTemporaryFile
try:
    from urllib2 import URLError
    from cStringIO import StringIO
except ImportError:  # Python 3
    from io import StringIO
    from urllib.error import URLError

from unittest import TestCase
from unittest import TestSuite
from unittest import TestLoader

from bvc import checker
from bvc.logger import logger
from bvc.checker import VersionsChecker
from bvc.checker import UnusedVersionsChecker
from bvc.scripts import indent_buildout
from bvc.scripts import find_unused_versions
from bvc.scripts import check_buildout_updates
from bvc.configparser import VersionsConfigParser


class LazyVersionsChecker(VersionsChecker):
    """
    VersionsChecker who does nothing at the initialisation
    excepting recording the arguments.
    """

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)


class LazyUnusedVersionsChecker(UnusedVersionsChecker):
    """
    UnusedVersionsChecker who does nothing at the
    initialisation excepting recording the arguments.
    """

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)


class URLOpener(object):
    """
    Fake urlopen.
    """
    results = {
        'egg': {
            'releases': ['0.3', '0.2']
        },
        'egg-dev': {
            'releases': ['1.0', '1.1b1']
        },
        'error-egg': [],
    }

    def __call__(self, url):
        package = url.split('/')[-2]
        try:
            return StringIO(json.dumps(self.results[package]))
        except KeyError:
            raise URLError('404')


class StubbedURLOpenTestCase(TestCase):
    """
    TestCase enabling a stub around the urllib2.urlopen
    used by VersionsChecker.
    """

    def setUp(self):
        self.stub_url_open()
        super(StubbedURLOpenTestCase, self).setUp()

    def tearDown(self):
        self.unstub_url_open()
        super(StubbedURLOpenTestCase, self).tearDown()

    def stub_url_open(self):
        """
        Replace the urlopen used in bvc.
        """
        self.original_url_open = checker.urlopen
        checker.urlopen = URLOpener()

    def unstub_url_open(self):
        """
        Restaure the original urlopen function.
        """
        checker.urlopen = self.original_url_open


class StubbedListDirTestCase(TestCase):
    """
    TestCase for faking the os.listdir calls.
    """
    listdir_content = []

    def setUp(self):
        self.stub_listdir()
        super(StubbedListDirTestCase, self).setUp()

    def tearDown(self):
        self.unstub_listdir()
        super(StubbedListDirTestCase, self).tearDown()

    def stub_listdir(self):
        """
        Replace the os.listdir function.
        """
        self.original_listdir = os.listdir
        os.listdir = lambda x: self.listdir_content

    def unstub_listdir(self):
        """
        Restaure the original os.listdir function.
        """
        os.listdir = self.original_listdir


class DictHandler(Handler):
    """
    Logging handler to check for expected logs.
    """

    def __init__(self, *ka, **kw):
        self.messages = {
            'debug': [], 'info': [],
            'warning': [], 'error': [],
            'critical': []
        }
        super(DictHandler, self).__init__(*ka, **kw)

    def emit(self, record):
        self.messages[record.levelname.lower()
                      ].append(record.getMessage())


class LogsTestCase(TestCase):
    """
    TestCase allowing to check the messages
    emitted by the logs.
    """

    def setUp(self):
        self.logs = DictHandler()
        logger.addHandler(self.logs)
        super(LogsTestCase, self).setUp()

    def tearDown(self):
        logger.removeHandler(self.logs)
        super(LogsTestCase, self).tearDown()

    def assertLogs(self, debug=[], info=[], warning=[],
                   error=[], critical=[]):
        expected = {'debug': debug, 'info': info,
                    'warning': warning, 'error': error,
                    'critical': critical}
        for key, item in expected.items():
            self.assertEquals(self.logs.messages[key],
                              item)


class StdOutTestCase(TestCase):
    """
    TestCase for capturing printed output on stdout.
    """

    def setUp(self):
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        sys.stdout = self.output
        sys.stderr = self.output
        super(StdOutTestCase, self).setUp()

    def tearDown(self):
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr
        super(StdOutTestCase, self).tearDown()

    def assertStdOut(self, output):
        self.assertEquals(self.output.getvalue(),
                          output)

    def assertInStdOut(self, output):
        self.assertTrue(output in self.output.getvalue())


class VersionsCheckerTestCase(StubbedURLOpenTestCase):

    def setUp(self):
        self.checker = LazyVersionsChecker(
            service_url='http://custom.pypi.org/pypi')
        super(VersionsCheckerTestCase, self).setUp()

    def test_parse_versions(self):
        config_file = NamedTemporaryFile()
        config_file.write('[sections]\nKey=Value\n'.encode('utf-8'))
        config_file.seek(0)
        self.assertEquals(self.checker.parse_versions(config_file.name),
                          [])
        config_file.seek(0)
        config_file.write('[VERSIONS]\negg=0.1\nEgg = 0.2'.encode('utf-8'))
        config_file.seek(0)
        self.assertEquals(self.checker.parse_versions(config_file.name),
                          [])
        config_file.seek(0)
        config_file.write('[versions]\negg=0.1\nEgg = 0.2'.encode('utf-8'))
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

    def test_build_specifiers(self):
        self.assertEquals(
            self.checker.build_specifiers(
                ('Django', 'zc.buildout'),
                {'django': '<=1.8',
                 'extra': '!=1.2'}),
            [('Django', '<=1.8'), ('zc.buildout', '')])

    def test_fetch_last_versions(self):
        self.assertEquals(
            self.checker.fetch_last_versions(
                [('egg', ''), ('UnknowEgg', '')], False,
                'service_url', 1, 1),
            [('egg', '0.3'), ('UnknowEgg', '0.0.0')])
        self.assertEquals(
            self.checker.fetch_last_versions(
                [('egg', '<=0.2'), ('UnknowEgg', '>1.0')], False,
                'service_url', 1, 1),
            [('egg', '0.2'), ('UnknowEgg', '0.0.0')])
        results = self.checker.fetch_last_versions(
            [('egg', ''), ('UnknowEgg', '')], False,
            'service_url', 1, 2)
        self.assertEquals(
            dict(results),
            dict([('egg', '0.3'), ('UnknowEgg', '0.0.0')]))

    def test_fetch_last_version(self):
        self.assertEquals(
            self.checker.fetch_last_version(
                ('UnknowEgg', ''), False, 'service_url', 1),
            ('UnknowEgg', '0.0.0')
        )
        self.assertEquals(
            self.checker.fetch_last_version(
                ('egg', ''), False, 'service_url', 1),
            ('egg', '0.3')
        )
        self.assertEquals(
            self.checker.fetch_last_version(
                ('egg', '<0.3'), False, 'service_url', 1),
            ('egg', '0.2')
        )

    def test_fetch_last_version_with_prereleases(self):
        self.assertEquals(
            self.checker.fetch_last_version(
                ('egg-dev', ''), False, 'service_url', 1),
            ('egg-dev', '1.0')
        )
        self.assertEquals(
            self.checker.fetch_last_version(
                ('egg-dev', ''), True, 'service_url', 1),
            ('egg-dev', '1.1b1')
        )
        self.assertEquals(
            self.checker.fetch_last_version(
                ('egg-dev', '<1.1'), True, 'service_url', 1),
            ('egg-dev', '1.0')
        )
        self.assertEquals(
            self.checker.fetch_last_version(
                ('egg-dev', '<=1.1'), True, 'service_url', 1),
            ('egg-dev', '1.1b1')
        )

    def test_find_updates(self):
        versions = OrderedDict([('egg', '1.5.1'), ('Egg', '0.0.0')])
        last_versions = OrderedDict([('egg', '1.5.1'), ('Egg', '1.0')])
        self.assertEquals(self.checker.find_updates(
            versions, last_versions), [('Egg', '1.0')])


class UnusedVersionsCheckerTestCase(StubbedListDirTestCase):

    def setUp(self):
        self.checker = LazyUnusedVersionsChecker()
        super(UnusedVersionsCheckerTestCase, self).setUp()

    def test_get_used_versions(self):
        self.listdir_content = ['file',
                                'package-1.0.egg',
                                'composed_egg-1.0.egg']
        self.assertEquals(self.checker.get_used_versions('.'),
                          ['package', 'composed_egg'])

    def test_get_find_unused_versions(self):
        self.assertEquals(
            self.checker.find_unused_versions(
                ['egg', 'CAPegg', 'composed-egg', 'unused'],
                ['Egg', 'capegg', 'composed_egg']),
            ['unused'])


class VersionsConfigParserTestCase(TestCase):

    def test_parse_case_insensitive(self):
        config_file = NamedTemporaryFile()
        config_file.write('[Section]\nKEY=VALUE\nKey=Value\n'.encode('utf-8'))
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.read(config_file.name)
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
        config_parser.write_section(config_file, 'Section', 24, '')
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            'Option                  = Value\n'
            'Option-void             = \n'
            'Option-multiline        = Value1\n'
            '                          Value2\n')
        config_file.close()

    def test_write_section_alpha_sorting(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section')
        config_parser.set('Section', 'Option-multiline', 'Value1\nValue2')
        config_parser.set('Section', 'Option-void', None)
        config_parser.set('Section', 'Option', 'Value')
        config_parser.write_section(config_file, 'Section', 24, 'alpha')
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            'Option                  = Value\n'
            'Option-multiline        = Value1\n'
            '                          Value2\n'
            'Option-void             = \n')
        config_file.close()

    def test_write_section_length_sorting(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section')
        config_parser.set('Section', 'Option-multiline', 'Value1\nValue2')
        config_parser.set('Section', 'Option-void', None)
        config_parser.set('Section', 'Option-size', None)
        config_parser.set('Section', 'Option', 'Value')
        config_parser.write_section(config_file, 'Section', 24, 'length')
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            'Option                  = Value\n'
            'Option-size             = \n'
            'Option-void             = \n'
            'Option-multiline        = Value1\n'
            '                          Value2\n')
        config_file.close()

    def test_write_section_low_indentation(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section')
        config_parser.set('Section', 'Option', 'Value')
        config_parser.set('Section', 'Option-void', None)
        config_parser.set('Section', 'Option-multiline', 'Value1\nValue2')
        config_parser.write_section(config_file, 'Section', 12, '')
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
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
        config_parser.set('Section 1', 'Option-add+', 'Value added')
        config_parser.set('Section 2', 'Option-multiline', 'Value1\nValue2')
        config_parser.set('Section 2', '<', 'Value1\nValue2')
        config_parser.write(config_file.name)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section 1]\n'
            'Option                          = Value\n'
            'Option-void                     = \n'
            'Option-add                     += Value added\n'
            '\n'
            '[Section 2]\n'
            'Option-multiline                = Value1\n'
            '                                  Value2\n'
            '<=                                Value1\n'
            '                                  Value2\n')
        config_file.close()

    def test_write_alpha_sorting(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section 1')
        config_parser.add_section('Section 2')
        config_parser.set('Section 1', 'Option', 'Value')
        config_parser.set('Section 1', 'Option-void', None)
        config_parser.set('Section 1', 'Option-add+', 'Value added')
        config_parser.set('Section 2', 'Option-multiline', 'Value1\nValue2')
        config_parser.set('Section 2', '<', 'Value1\nValue2')
        config_parser.write(config_file.name, sorting='alpha')
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section 1]\n'
            'Option                          = Value\n'
            'Option-add                     += Value added\n'
            'Option-void                     = \n'
            '\n'
            '[Section 2]\n'
            '<=                                Value1\n'
            '                                  Value2\n'
            'Option-multiline                = Value1\n'
            '                                  Value2\n')
        config_file.close()

    def test_write_low_indentation(self):
        config_file = NamedTemporaryFile()
        config_parser = VersionsConfigParser()
        config_parser.add_section('Section 1')
        config_parser.add_section('Section 2')
        config_parser.set('Section 1', 'Option', 'Value')
        config_parser.set('Section 1', 'Option-void', None)
        config_parser.set('Section 2', 'Option-multiline', 'Value1\nValue2')
        config_parser.write(config_file.name, 12)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section 1]\n'
            'Option      = Value\n'
            'Option-void = \n'
            '\n'
            '[Section 2]\n'
            'Option-multiline= Value1\n'
            '              Value2\n')
        config_file.close()

    def test_parse_and_write_buildout_operators(self):
        config_file = NamedTemporaryFile()
        config_file.write(
            '[Section]\nAd+=dition\nSub-=straction'.encode('utf-8'))
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.read(config_file.name)
        config_file.seek(0)
        config_parser.write(config_file.name, 24)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            'Ad                     += dition\n'
            'Sub                    -= straction\n')
        config_file.close()

    def test_parse_and_write_buildout_operators_offset(self):
        config_file = NamedTemporaryFile()
        config_file.write(
            '[Section]\nAd  +=dition\nSub - = straction'.encode('utf-8'))
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.read(config_file.name)
        config_file.seek(0)
        config_parser.write(config_file.name, 24)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            'Ad                     += dition\n'
            'Sub                    -= straction\n')
        config_file.close()

    def test_parse_and_write_buildout_operators_multilines(self):
        config_file = NamedTemporaryFile()
        config_file.write(
            '[Section]\nAdd+=Multi\n  Lines'.encode('utf-8'))
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.read(config_file.name)
        config_file.seek(0)
        config_parser.write(config_file.name, 24)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            'Add                    += Multi\n'
            '                          Lines\n')
        config_file.close()

    def test_parse_and_write_buildout_macros(self):
        config_file = NamedTemporaryFile()
        config_file.write(
            '[Section]\n<=Macro\n Template'.encode('utf-8'))
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.read(config_file.name)
        config_file.seek(0)
        config_parser.write(config_file.name, 24)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            '<=                        Macro\n'
            '                          Template\n')
        config_file.close()

    def test_parse_and_write_buildout_macros_offset(self):
        config_file = NamedTemporaryFile()
        config_file.write(
            '[Section]\n<  = Macro\n  Template'.encode('utf-8'))
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.read(config_file.name)
        config_file.seek(0)
        config_parser.write(config_file.name, 24)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section]\n'
            '<=                        Macro\n'
            '                          Template\n')
        config_file.close()

    def test_parse_and_write_buildout_conditional_sections(self):
        config_file = NamedTemporaryFile()
        config_file.write('[Section:Condition]\nKey=Value\n'.encode('utf-8'))
        config_file.seek(0)
        config_parser = VersionsConfigParser()
        config_parser.read(config_file.name)
        config_file.seek(0)
        config_parser.write(config_file.name, 24)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[Section:Condition]\n'
            'Key                     = Value\n')
        config_file.close()


class FindUnusedVersionsTestCase(LogsTestCase,
                                 StdOutTestCase,
                                 StubbedListDirTestCase):
    listdir_content = [
        'egg-1.0.egg',
        'composed_egg-1.0.egg']

    def test_simple(self):
        config_file = NamedTemporaryFile()
        config_file.write('[versions]\nEgg=1.0\n'
                          'Unused-egg=1.0\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline(config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            info=['- 2 versions found in %s.' % config_file.name,
                  '- 2 packages need to be checked for updates.'],
            warning=['- Unused-egg is unused.'])
        self.assertStdOut('- Unused-egg is unused.\n')
        config_file.close()

    def test_write(self):
        config_file = NamedTemporaryFile()
        config_file.write('[versions]\nEgg=1.0\n'
                          'Unused-egg=1.0\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline('%s -w' % config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            info=['- 2 versions found in %s.' % config_file.name,
                  '- 2 packages need to be checked for updates.',
                  '- %s updated.' % config_file.name],
            warning=['- Unused-egg is unused.'])
        self.assertStdOut('- Unused-egg is unused.\n')
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[versions]\nEgg                             = 1.0\n')

    def test_no_source(self):
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline('')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            debug=["'versions' section not found in versions.cfg."],
            info=['- 0 packages need to be checked for updates.'])
        self.assertStdOut('')

    def test_exclude(self):
        config_file = NamedTemporaryFile()
        config_file.write('[versions]\nEgg=1.0\n'
                          'Unused-egg=1.0\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline('%s -e unused-egg' %
                                         config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            info=['- 2 versions found in %s.' % config_file.name,
                  '- 1 packages need to be checked for updates.'])
        self.assertStdOut('')
        config_file.close()

    def test_output_max(self):
        config_file = NamedTemporaryFile()
        config_file.write('[versions]\nEgg=1.0\n'
                          'Unused-egg=1.0\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline('%s -vvv' % config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            info=['- 2 versions found in %s.' % config_file.name,
                  '- 2 packages need to be checked for updates.'],
            warning=['- Unused-egg is unused.'])
        self.assertStdOut(
            '- 2 versions found in %s.\n'
            '- 2 packages need to be checked for updates.\n'
            '- Unused-egg is unused.\n' % config_file.name)
        config_file.close()

    def test_output_none(self):
        config_file = NamedTemporaryFile()
        config_file.write('[versions]\nEgg=1.0\n'
                          'Unused-egg=1.0\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline('%s -q' % config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline('invalid -qqqq')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')
        config_file.close()

    def test_handle_error(self):
        original_listdir_content = self.listdir_content
        self.listdir_content = 42
        config_file = NamedTemporaryFile()
        config_file.write('[versions]\n'.encode('utf-8'))
        with self.assertRaises(SystemExit) as context:
            find_unused_versions.cmdline('%s' % config_file.name)
        self.assertEqual(context.exception.code,
                         "'int' object is not iterable")
        self.listdir_content = original_listdir_content


class IndentCommandLineTestCase(LogsTestCase,
                                StdOutTestCase):

    def test_simple(self):
        config_file = NamedTemporaryFile()
        config_file.write('[sections]\nKey=Value\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('%s' % config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            warning=['- %s (re)indented at 32 spaces.' % config_file.name])
        self.assertStdOut(
            '- %s (re)indented at 32 spaces.\n' % config_file.name)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[sections]\n'
            'Key                             = Value\n')
        config_file.close()

    def test_invalid_source(self):
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('invalid.cfg')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(warning=['- invalid.cfg cannot be read.'])
        self.assertStdOut('- invalid.cfg cannot be read.\n')

    def test_multiple_sources(self):
        config_file = NamedTemporaryFile()
        config_file.write('[sections]\nKey=Value\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('%s invalid.cfg' % config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            warning=['- %s (re)indented at 32 spaces.' % config_file.name,
                     '- invalid.cfg cannot be read.'])
        self.assertStdOut(
            '- %s (re)indented at 32 spaces.\n'
            '- invalid.cfg cannot be read.\n' % config_file.name)

    def test_no_source(self):
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            warning=['No files to (re)indent'])
        self.assertStdOut(
            'No files to (re)indent\n')

    def test_output_none(self):
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('invalid.cfg -q')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('source.cfg -qqqqqqq')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')


class CheckUpdatesCommandLineTestCase(LogsTestCase,
                                      StdOutTestCase,
                                      StubbedURLOpenTestCase):

    def test_no_args_no_source(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            debug=["'versions' section not found in versions.cfg."],
            info=['- 0 packages need to be checked for updates.',
                  '- 0 package updates found.'])
        self.assertStdOut('')

    def test_include_no_source(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            debug=["'versions' section not found in versions.cfg.",
                   '-> Last version of egg is 0.3.',
                   '=> egg current version (0.0.0) and '
                   'last version (0.3) are different.'],
            info=['- 1 packages need to be checked for updates.',
                  '> Fetching latest datas for egg...',
                  '- 1 package updates found.'],
            warning=['[versions]',
                     'egg                             = 0.3'])
        self.assertStdOut(
            '[versions]\n'
            'egg                             = 0.3\n')

    def test_include_unavailable(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i unavailable')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            debug=["'versions' section not found in versions.cfg.",
                   '!> http://pypi.python.org/pypi/unavailable/json 404',
                   '-> Last version of unavailable is 0.0.0.'],
            info=['- 1 packages need to be checked for updates.',
                  '> Fetching latest datas for unavailable...',
                  '- 0 package updates found.'])
        self.assertStdOut('')

    def test_include_exclude(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i unavailable -e unavailable')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            debug=["'versions' section not found in versions.cfg."],
            info=['- 0 packages need to be checked for updates.',
                  '- 0 package updates found.'])
        self.assertStdOut('')

    def test_write_include_in_blank(self):
        config_file = NamedTemporaryFile()
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline(
                '-i egg -w %s' % config_file.name)
        self.assertEqual(context.exception.code, 0)
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[versions]\negg                             = 0.3\n')
        self.assertStdOut(
            '[versions]\negg                             = 0.3\n')

    def test_write_in_existing_file_with_exclude(self):
        config_file = NamedTemporaryFile()
        config_file.write(
            '[buildout]\ndevelop=.\n'
            '[versions]\nexcluded=1.0\negg=0.1'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline(
                '-e excluded -w %s' % config_file.name)
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(
            debug=['-> Last version of egg is 0.3.',
                   '=> egg current version (0.1) and '
                   'last version (0.3) are different.'],
            info=['- 2 versions found in %s.' % config_file.name,
                  '- 1 packages need to be checked for updates.',
                  '> Fetching latest datas for egg...',
                  '- 1 package updates found.',
                  '- %s updated.' % config_file.name],
            warning=['[versions]',
                     'egg                             = 0.3'])
        config_file.seek(0)
        self.assertEquals(
            config_file.read().decode('utf-8'),
            '[buildout]\n'
            'develop                         = .\n\n'
            '[versions]\n'
            'excluded                        = 1.0\n'
            'egg                             = 0.3\n')
        self.assertStdOut(
            '[versions]\n'
            'egg                             = 0.3\n')

    def test_output_default(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut(
            '[versions]\n'
            'egg                             = 0.3\n')

    def test_output_with_plus_and_minus(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -vvv -qqq')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut(
            '[versions]\n'
            'egg                             = 0.3\n')

    def test_output_none(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -q')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -qqqqqqqq')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')

    def test_output_increased(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -v')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut(
            '- 1 packages need to be checked for updates.\n'
            '> Fetching latest datas for egg...\n'
            '- 1 package updates found.\n'
            '[versions]\n'
            'egg                             = 0.3\n')

    def test_output_max(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -vvvvvvvvvv')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut(
            "'versions' section not found in versions.cfg.\n"
            "- 1 packages need to be checked for updates.\n"
            "> Fetching latest datas for egg...\n"
            "-> Last version of egg is 0.3.\n"
            "=> egg current version (0.0.0) and "
            "last version (0.3) are different.\n"
            "- 1 package updates found.\n"
            "[versions]\n"
            "egg                             = 0.3\n")

    def test_output_max_specifiers(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -s egg:<0.3 -vvv')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut(
            "'versions' section not found in versions.cfg.\n"
            "- 1 packages need to be checked for updates.\n"
            "> Fetching latest datas for egg...\n"
            "-> Last version of egg<0.3 is 0.2.\n"
            "=> egg current version (0.0.0) and "
            "last version (0.2) are different.\n"
            "- 1 package updates found.\n"
            "[versions]\n"
            "egg                             = 0.2\n")

    def test_specifiers_errors(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -s egg<0.3')
        self.assertEqual(context.exception.code, 2)
        self.assertInStdOut('error: argument -s/--specifier: '
                            'key:value syntax not followed')

        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i egg -s egg:')
        self.assertEqual(context.exception.code, 2)
        self.assertInStdOut('error: argument -s/--specifier: '
                            'key or value are empty')

    def test_handle_error(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i error-egg')
        self.assertEqual(context.exception.code,
                         "list indices must be integers, not str")


loader = TestLoader()

test_suite = TestSuite(
    [loader.loadTestsFromTestCase(VersionsCheckerTestCase),
     loader.loadTestsFromTestCase(UnusedVersionsCheckerTestCase),
     loader.loadTestsFromTestCase(VersionsConfigParserTestCase),
     loader.loadTestsFromTestCase(IndentCommandLineTestCase),
     loader.loadTestsFromTestCase(FindUnusedVersionsTestCase),
     loader.loadTestsFromTestCase(CheckUpdatesCommandLineTestCase)
     ]
)
