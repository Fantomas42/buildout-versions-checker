"""Tests for Buildout version checker"""
import sys
from logging import Handler
from collections import OrderedDict
from tempfile import NamedTemporaryFile
try:
    from cStringIO import StringIO
except ImportError:  # Python 3
    from io import StringIO

from unittest import TestCase
from unittest import TestSuite
from unittest import TestLoader

from bvc import checker
from bvc.logger import logger
from bvc.checker import VersionsChecker
from bvc.scripts import indent_buildout
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


class PypiServerProxy(object):
    """
    Fake Pypi proxy server.
    """
    results = {
        'egg': [
            {'name': 'Egg', 'version': '0.2'},
            {'name': 'EGG', 'version': '0.3'},
            {'name': 'eggtractor', 'version': '0.42'}
        ],
        'error-egg': [{}],
    }

    def __init__(*ka, **kw):
        pass

    def search(self, query_dict):
        try:
            return self.results[query_dict['name']]
        except KeyError:
            pass
        return []


class StubbedServerProxyTestCase(TestCase):
    """
    TestCase enabling a stub around the ServerProxy
    class used by VersionsChecker.
    """
    def setUp(self):
        self.stub_server_proxy()
        super(StubbedServerProxyTestCase, self).setUp()

    def tearDown(self):
        self.unstub_server_proxy()
        super(StubbedServerProxyTestCase, self).tearDown()

    def stub_server_proxy(self):
        """
        Replace the ServerProxy class used in bvc.
        """
        self.original_server_proxy = checker.ServerProxy
        checker.ServerProxy = PypiServerProxy

    def unstub_server_proxy(self):
        """
        Restaure the original ServerProxy class.
        """
        checker.ServerProxy = self.original_server_proxy


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
        sys.stdout = self.output
        super(StdOutTestCase, self).setUp()

    def tearDown(self):
        sys.stdout = self.saved_stdout
        #self.output.close()
        super(StdOutTestCase, self).tearDown()

    def assertStdOut(self, output):
        self.assertEquals(self.output.getvalue(),
                          output)


class VersionsCheckerTestCase(StubbedServerProxyTestCase):

    def setUp(self):
        self.checker = LazyVersionsChecker()
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

    def test_fetch_last_versions(self):
        self.assertEquals(
            self.checker.fetch_last_versions(
                ['egg', 'UnknowEgg'], 'service_url', 1, 1),
            [('egg', '0.3'), ('UnknowEgg', '0.0.0')])
        results = self.checker.fetch_last_versions(
            ['egg', 'UnknowEgg'], 'service_url', 1, 2)
        self.assertEquals(
            dict(results),
            dict([('egg', '0.3'), ('UnknowEgg', '0.0.0')]))

    def test_fetch_last_version(self):
        self.assertEquals(
            self.checker.fetch_last_version('UnknowEgg', 'service_url', 1),
            ('UnknowEgg', '0.0.0')
        )
        self.assertEquals(
            self.checker.fetch_last_version('egg', 'service_url', 1),
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


class IndentCommandLineTestCase(LogsTestCase,
                                StdOutTestCase):

    def test_simple(self):
        config_file = NamedTemporaryFile()
        config_file.write('[sections]\nKey=Value\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('-s %s' % config_file.name)
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
            indent_buildout.cmdline('-s invalid.cfg')
        self.assertEqual(context.exception.code, 0)
        self.assertLogs(warning=['- invalid.cfg cannot be read.'])
        self.assertStdOut('- invalid.cfg cannot be read.\n')

    def test_multiple_sources(self):
        config_file = NamedTemporaryFile()
        config_file.write('[sections]\nKey=Value\n'.encode('utf-8'))
        config_file.seek(0)
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('-s %s -s invalid.cfg' % config_file.name)
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
            indent_buildout.cmdline('-s invalid.cfg -q')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')
        with self.assertRaises(SystemExit) as context:
            indent_buildout.cmdline('-s source.cfg -qqqqqqq')
        self.assertEqual(context.exception.code, 0)
        self.assertStdOut('')


class CheckUpdatesCommandLineTestCase(LogsTestCase,
                                      StdOutTestCase,
                                      StubbedServerProxyTestCase):

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
                '-i egg -w -s %s' % config_file.name)
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
                '-e excluded -w -s %s' % config_file.name)
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

    def test_handle_error(self):
        with self.assertRaises(SystemExit) as context:
            check_buildout_updates.cmdline('-i error-egg')
        self.assertEqual(context.exception.code, "'name'")


loader = TestLoader()

test_suite = TestSuite(
    [loader.loadTestsFromTestCase(VersionsCheckerTestCase),
     loader.loadTestsFromTestCase(VersionsConfigParserTestCase),
     loader.loadTestsFromTestCase(IndentCommandLineTestCase),
     loader.loadTestsFromTestCase(CheckUpdatesCommandLineTestCase)
     ]
)
