"""Setup script for bvc"""
import os

from setuptools import setup
from setuptools import find_packages

__version__ = '0.3'
__license__ = 'BSD License'

__author__ = 'Fantomas42'
__email__ = 'fantomas42@gmail.com'

__url__ = 'https://github.com/Fantomas42/bvc'


setup(
    name='bvc',
    version=__version__,
    zip_safe=False,

    packages=find_packages(exclude=['tests']),
    include_package_data=True,

    author=__author__,
    author_email=__email__,
    url=__url__,

    license=__license__,
    platforms='any',
    description='Check updates from a Buildout version file',
    long_description=open(os.path.join('README.rst')).read(),
    keywords='buildout, versions, updates',
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    install_requires=['futures>=2.1.4'],
    entry_points={
        'console_scripts': 'check-buildout-updates=bvc:cmdline'},
)
