"""Config parser for Buildout Versions Checker"""
import re

from itertools import chain
try:
    from ConfigParser import RawConfigParser
except ImportError:  # Python 3
    from configparser import RawConfigParser

from bvc.indentation import perfect_indentation

OPERATORS = re.compile(r'[+-]$')


class VersionsConfigParser(RawConfigParser):
    """
    ConfigParser customized to read and write
    beautiful buildout files.
    """
    optionxform = str

    def __init__(self, *args, **kwargs):
        self.sorting = kwargs.pop('sorting', None)
        self.indentation = kwargs.pop('indentation', -1)
        RawConfigParser.__init__(self, *args, **kwargs)

    def ascii_sorter(self, items):
        return sorted(items, key=lambda x: x[0])

    def alpha_sorter(self, items):
        return sorted(items, key=lambda x: x[0].lower())

    def length_sorter(self, items):
        return sorted(self.alpha_sorter(items),
                      key=lambda x: len(x[0]))

    def write_section(self, fd, section, indentation, sorting):
        """
        Write a section of an .ini-format
        and all the keys within.
        """
        string_section = '[%s]\n' % section

        items = self._sections[section].items()
        try:
            items = getattr(self, '%s_sorter' % sorting)(items)
        except (TypeError, AttributeError):
            pass

        for key, value in items:
            if key == '__name__':
                continue
            if value is None:
                value = ''
            operator = ''
            buildout_operator = OPERATORS.search(key)
            if buildout_operator:
                operator = buildout_operator.group(0)
                key = key[:-1]
            if key == '<':
                value = '{value:>{indent}}'.format(
                    value=value, indent=indentation + len(value) - 1)
            else:
                key = '{key:<{indent}}{operator}'.format(
                    key=key, operator=operator,
                    indent=max(indentation - int(bool(operator)), 0))
            value = value.replace('\n', '{:<{indent}}'.format(
                '\n', indent=indentation + 3))
            string_section += '{key}{operator:<{indent}}{value}\n'.format(
                key=key, operator='=', value=value,
                indent=int(bool(indentation)) + 1)

        fd.write(string_section.encode('utf-8'))

    def write(self, source):
        """
        Write an .ini-format representation of the
        configuration state with a readable indentation.
        """
        if self.indentation < 0:
            self.indentation = self.perfect_indentation

        with open(source, 'wb') as fd:
            sections = list(self._sections.keys())
            for section in sections[:-1]:
                self.write_section(fd, section,
                                   self.indentation, self.sorting)
                fd.write('\n'.encode('utf-8'))
            self.write_section(fd, sections[-1],
                               self.indentation, self.sorting)

    @property
    def perfect_indentation(self, rounding=4):
        """
        Find the perfect indentation required for writing
        the file, by iterating over the different options.
        """
        return perfect_indentation(
            chain(*[self.options(section) for section in self.sections()])
        )
