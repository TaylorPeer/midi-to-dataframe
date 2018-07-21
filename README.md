# MIDI-to-DataFrame
Python 3 library for converting between MIDI files and *Pandas* **DataFrame** objects for use in generative and predictive machine learning applications using symbolic music as training and evaluation material.

## Requirements:
Reading and writing to MIDI format is made possible by vishnubob's **python-midi** project (https://github.com/vishnubob/python-midi). To enable Python 3 support, this dependency must be installed from a specific branch:

* `pip3 install git+https://github.com/vishnubob/python-midi.git@feature/python3`

## Installation:
Once the above requirement has been installed, midi-to-dataframe can be installed as follows:

* `pip3 install git+https://github.com/TaylorPeer/midi-to-dataframe`

## Usage

Basic usage and configuration is demonstrated in the **basics** *Jupyter* notebook: https://github.com/TaylorPeer/midi-to-dataframe/blob/master/examples/basics.ipynb

## Known Issues

* Calculation of beat/measure information is incorrect for MIDI files using time signatures other than 4/4.
