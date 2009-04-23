#!/usr/bin/env python

import sys
from distutils.core import setup

a, b, c, d, e = sys.version_info
if a < 2 or b < 5:
    es = "ZDStack requires Python 2.5 or greater, your version is [%s]"
    print >> sys.stderr, es % ([str(x) for x in [a, b, c]])
    sys.exit(1)

setup(name='ZDStack',
      version='0.11.0',
      description='ZDStack zserv ZDaemon Server Wrapper',
      author='Charlie Gunyon',
      author_email='charles.gunyon@gmail.com',
      url='http://zdstack.googlecode.com/',
      scripts=['bin/zdstack', 'bin/zservctl', 'bin/fakezserv', 'bin/zdrpc',
               'bin/zdsweb'],
      packages=['ZDStack'],
      requires=['sqlalchemy>=0.5.3'],
)
