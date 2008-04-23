#!python -u

from distutils.core import setup

setup(name='ZDStack',
      version='0.1',
      description='ZDStack zserv ZDaemon Server Wrapper',
      author='Charlie Gunyon',
      author_email='charles.gunyon@gmail.com',
      url='http://zdstack.googlecode.com/',
      scripts=['bin/zdstackctl'],
      packages=['ZDStack'],
     )
