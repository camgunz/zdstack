#!/usr/bin/env python

from distutils.core import setup

setup(name='ZDStack',
      version='0.9.1',
      description='ZDStack zserv ZDaemon Server Wrapper',
      author='Charlie Gunyon',
      author_email='charles.gunyon@gmail.com',
      url='http://zdstack.googlecode.com/',
      scripts=['bin/zdstack', 'bin/zservctl'],
      packages=['ZDStack'],
     )
