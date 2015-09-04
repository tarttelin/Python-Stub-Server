#!/usr/bin/env python

from setuptools import setup
import stubserver

setup(name='stubserver',
      version=stubserver.__version__,
      description=stubserver.__doc__,
      author=stubserver.__author__,
      author_email=stubserver.__email__,
      url=stubserver.__url__,
      packages=['stubserver'],
      licence='FreeBSD',
      test_suite='test',
      keywords=['test', 'unittest', 'mock', 'http', 'ftp'],
      classifiers=[
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.7',
      ]
     )
