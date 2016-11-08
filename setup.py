"""Setup script for bvc"""
import os
import sys

from setuptools import find_packages
from setuptools import setup

__version__ = '1.9.4'
__license__ = 'BSD License'

__author__ = 'Fantomas42'
__email__ = 'fantomas42@gmail.com'

__url__ = 'https://github.com/Fantomas42/buildout-versions-checker'


install_requires = ['six', 'packaging']
if sys.version_info.major == 2:
    install_requires.append('futures')

setup(
    name='buildout-versions-checker',
    version=__version__,
    zip_safe=False,

    packages=find_packages(exclude=['tests']),
    include_package_data=True,

    author=__author__,
    author_email=__email__,
    url=__url__,

    license=__license__,
    platforms='any',
    description='Checks egg updates in your Buildout configurations.',
    long_description=open(os.path.join('README.rst')).read(),
    keywords='buildout, versions, updates',
    classifiers=[
        'Framework :: Buildout',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: BSD License',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'indent-buildout=bvc.scripts.indent_buildout:cmdline',
            'find-unused-versions=bvc.scripts.find_unused_versions:cmdline',
            'check-buildout-updates=bvc.scripts.check_buildout_updates:cmdline'
        ]
    },
    test_suite='bvc.tests.test_suite',
)
