#!/usr/bin/env python

from distutils.core import setup

setup(name='stubserver',
      version='0.1',
      description='''A stub webserver used to enable blackbox testing of applications that call external web urls.  
      For example, an application that consumes data from an external REST api.  The usage pattern is intended to be very
      much like using a mock framework.''',
      author='Chris Tarttelin and Point 2 inc',
      author_email='ctarttelin@point2.com',
      url='http://www.pyruby.com/pythonstubserver',
      py_modules=['stubserver'],
     )
