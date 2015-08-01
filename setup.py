#!/usr/bin/env python

from setuptools import setup
pak = __import__('gforms')

setup(name='gForms',
    version=pak.__version__,
    description='A GUI form generator for data structues editing',
    author='Fernando Leite Pereira',
    author_email='fernando.pereira@cern.ch',
    url='',
    packages=['gforms_traits_patch'],
    py_modules=['gforms'],
    install_requires = ['traitsui'],
    dependency_links=['https://github.com/ferdonline/traitsui/archive/gforms.zip']
  )
