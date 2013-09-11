"""Config parser for Buildout Versions Checker"""
try:
    from ConfigParser import RawConfigParser
except ImportError:  # Python 3
    from configparser import RawConfigParser


class VersionsConfigParser(RawConfigParser):
    """
    ConfigParser customized to read and write
    beautiful buildout files.
    """
    optionxform = str

    def write_section(self, fd, section, indentation):
        """
        Write a section of an .ini-format
        and all the keys within.
        """
        string_section = '[%s]\n' % section
        for key, value in self._sections[section].items():
            if key != '__name__':
                if value is None:
                    value = ''
                string_section += '%s= %s\n' % (
                    key.ljust(indentation),
                    str(value).replace(
                        '\n', '\n'.ljust(indentation + 3)))
        fd.write(string_section.encode('utf-8'))

    def write(self, source, indentation=24):
        """
        Write an .ini-format representation of the
        configuration state with a readable indentation.
        """
        with open(source, 'wb') as fd:
            sections = list(self._sections.keys())
            for section in sections[:-1]:
                self.write_section(fd, section, indentation)
                fd.write('\n'.encode('utf-8'))
            self.write_section(fd, sections[-1], indentation)
