#!/usr/bin/env python
from setuptools import setup, find_packages

# Define version information
VERSION = '0.3'
FULLVERSION = VERSION

requirements = [
]

setup(name='midi_to_dataframe',
      version=VERSION,
      author='Taylor Peer',
      url='https://github.com/TaylorPeer/midi-to-dataframe',
      description="Python library for converting between MIDI files and Pandas DataFrame objects.",
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      packages=find_packages(),
      install_requires=requirements,
      package_data={}
      )
