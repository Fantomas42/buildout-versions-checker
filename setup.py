"""Setup script for bvc"""
import os

from setuptools import setup
from setuptools import find_packages

__version__ = '1.0'
__license__ = 'BSD License'

__author__ = 'Fantomas42'
__email__ = 'fantomas42@gmail.com'

__url__ = 'https://github.com/Fantomas42/buildout-versions-checker'


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
        'License :: OSI Approved :: BSD License',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    install_requires=['six>=1.4.1',
                      'futures>=2.1.4'],
    entry_points={
        'console_scripts': 'check-buildout-updates=bvc:cmdline'},
    test_suite='bvc.tests.test_suite',
)
