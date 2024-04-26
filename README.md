# MIDI-to-DataFrame
Python 3 library for converting between MIDI files and *Pandas* **DataFrame** objects for use in generative and predictive machine learning applications using symbolic music as training and evaluation material.

## Installation:
Once the above requirement has been installed, midi-to-dataframe can be installed as follows:

* `pip install midi-to-dataframe`

## Usage

Basic usage and configuration is demonstrated in the **basics** *Jupyter* notebook: https://github.com/TaylorPeer/midi-to-dataframe/blob/master/examples/basics.ipynb

## Known Issues

* Calculation of beat/measure information is incorrect for MIDI files using time signatures other than 4/4.
