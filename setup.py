#!/usr/bin/env python
from setuptools import setup, find_packages

# Define version information
VERSION = '0.1'
FULLVERSION = VERSION

requirements = [
]

setup(name='midi_to_dataframe',
      version=VERSION,
      # TODO: description="",
      author='Taylor Peer',
      # TODO: author_email='',
      url='https://github.com/TaylorPeer/midi-to-dataframe',
      # TODO: license='',
      packages=find_packages(),
      install_requires=requirements,
      package_data={},
      # TODO: classifiers=[]
      )
