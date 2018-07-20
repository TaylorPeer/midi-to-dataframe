#!/usr/bin/env python
from setuptools import setup, find_packages

# Define version information
VERSION = '0.1'
FULLVERSION = VERSION

requirements = [
]

setup(name='midi_to_dataframe',
      version=VERSION,
      author='Taylor Peer',
      url='https://github.com/TaylorPeer/midi-to-dataframe',
      packages=find_packages(),
      install_requires=requirements,
      package_data={}
      )
