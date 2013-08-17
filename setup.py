"""Setup script for bvc"""
import os

from setuptools import setup
from setuptools import find_packages

import bvc

setup(
    name='bvc',
    version=bvc.__version__,
    zip_safe=False,

    packages=find_packages(exclude=['tests']),
    include_package_data=True,

    author=bvc.__author__,
    author_email=bvc.__email__,
    url=bvc.__url__,

    license=bvc.__license__,
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
