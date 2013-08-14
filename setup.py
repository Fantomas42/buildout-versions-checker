"""Setup script for bvc"""
import os

from setuptools import setup
from setuptools import find_packages

setup(
    name='bvc',
    version=0.1,
    zip_safe=False,

    scripts=['./src/scripts/buildout_versions_check'],

    packages=find_packages(exclude=['tests']),
    include_package_data=True,

    author='Fantomas42',
    author_email='fantomas42@gmail.com',
    url='https://github.com/Fantomas42/bvc',

    license='GPL',
    platforms='any',
    description='Check updates from a Buildout version file',
    long_description=open(os.path.join('README.rst')).read(),
    keywords='buildout, versions, updates',
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    install_requires=['futures>=2.1.4'],
)
