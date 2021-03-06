#!/usr/bin/env python

from distutils.core import setup

setup(name='ZDStack',
      version='0.9',
      description='ZDStack zserv ZDaemon Server Wrapper',
      author='Charlie Gunyon',
      author_email='charles.gunyon@gmail.com',
      url='http://zdstack.googlecode.com/',
      scripts=['bin/zdstackctl', 'bin/zservctl'],
      packages=['ZDStack'],
     )
