from setuptools import setup

setup(
    name='midi_to_dataframe',
    version='0.1',
    scripts=['midi_to_dataframe'],
    install_requires=[
        'midi', 'pandas',
    ],
)
