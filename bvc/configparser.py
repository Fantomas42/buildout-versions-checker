"""Config parser for Buildout Versions Checker"""
import re
from operator import itemgetter
try:
    from ConfigParser import RawConfigParser
except ImportError:  # Python 3
    from configparser import RawConfigParser

OPERATORS = re.compile(r'[+-]$')


class VersionsConfigParser(RawConfigParser):
    """
    ConfigParser customized to read and write
    beautiful buildout files.
    """
    optionxform = str

    def alpha_sorter(self, items):
        return sorted(items, key=itemgetter(0))

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
                    indent=indentation - int(bool(operator)))
            value = value.replace('\n', '{:<{indent}}'.format(
                '\n', indent=indentation + 3))
            string_section += '{key}= {value}\n'.format(key=key, value=value)

        fd.write(string_section.encode('utf-8'))

    def write(self, source, indentation=32, sorting=None):
        """
        Write an .ini-format representation of the
        configuration state with a readable indentation.
        """
        with open(source, 'wb') as fd:
            sections = list(self._sections.keys())
            for section in sections[:-1]:
                self.write_section(fd, section, indentation, sorting)
                fd.write('\n'.encode('utf-8'))
            self.write_section(fd, sections[-1], indentation, sorting)
