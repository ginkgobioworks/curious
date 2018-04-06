#!/usr/bin/env python
from __future__ import print_function

import logging
import os
import sys
from subprocess import (
  CalledProcessError,
  STDOUT,
  check_output,
)

from setuptools import setup, Command


class BowerBuildCommand(Command):
  description = 'run bower commands [install by default]'
  user_options = [
    ('bower-command=', 'c', 'Bower command to run. Defaults to "install".'),
    ('force-latest', 'F', 'Force latest version on conflict.'),
    ('allow-root', 'R', 'Allow bower to be run as root.'),
    ('production', 'p', 'Do not install project devDependencies.'),
  ]
  boolean_options = ['production', 'force-latest', 'allow-root']

  def initialize_options(self):
    self.force_latest = False
    self.production = False
    self.bower_command = 'install'
    self.allow_root = False

  def finalize_options(self):
    pass

  def _run_with_output(self, *args, **kwargs):
    try:
      print(check_output(*args, **kwargs))
    except CalledProcessError as e:
      print(e.output, file=sys.stderr)
      raise e

  def run(self):
    cmd = ['bower', self.bower_command, '--no-color']
    if self.force_latest:
      cmd.append('-F')
    if self.production:
      cmd.append('-p')
    if self.allow_root:
      cmd.append('--allow-root')
    self._run_with_output(cmd, stderr=STDOUT)


class WebassetsBuildCommand(Command):
  description = 'compile web assets'

  user_options = [
    ('cache-dir=', 'c', 'Cache directory. Defaults to ".webassets-cache".'),
  ]

  def initialize_options(self):
    self.cache_dir = '.webassets-cache'

  def finalize_options(self):
    try:
      os.mkdir(self.cache_dir)
    except OSError:
      pass

  def run(self):
    from webassets import Bundle
    from webassets import Environment
    from webassets.script import CommandLineEnvironment

    css = Bundle('curious/src/css/app.css', output='curious/dist/curious.css')
    js = Bundle('curious/src/js/*.js', output='curious/dist/curious.js')
    jsmin = Bundle('curious/src/js/*.js', filters='jsmin', output='curious/dist/curious.min.js')
    jst = Bundle('curious/src/html/*.html', filters='jst', output='curious/dist/curious_jst.js')

    assets_env = Environment('./curious/static')
    assets_env.cache = self.cache_dir
    assets_env.register('css', css)
    assets_env.register('js', js)
    assets_env.register('jsmin', jsmin)
    assets_env.register('jst', jst)

    log = logging.getLogger('webassets')
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)

    cmdenv = CommandLineEnvironment(assets_env, log)
    cmdenv.build()


setup(
  name='curious',
  version='1.2.0',

  author='Benjie Chen, Ginkgo Bioworks',
  author_email='benjie@ginkgobioworks.com, devs@ginkgobioworks.com',

  description='Graph-based data exploration tool',
  long_description=open('README.rst').read(),
  url='https://github.com/ginkgobioworks/curious',

  license='MIT',
  keywords='graph query django sql curious database ginkgo',
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Environment :: Other Environment',
    'Framework :: Django :: 1.6',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: JavaScript',
    'Programming Language :: SQL',
    'Topic :: Database',
    'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
    'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    'Topic :: Scientific/Engineering :: Information Analysis',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Text Processing :: General',
  ],

  cmdclass={
    'build_assets': WebassetsBuildCommand,
    'install_bower': BowerBuildCommand,
  },

  packages=['curious'],
  include_package_data=True,
  zip_safe=True,

  setup_requires=[
    'webassets',
    'jsmin',
  ],
  install_requires=[
    'Django ~= 1.11',
    'humanize',
    'parsimonious == 0.5',
    'parsedatetime ~= 1.0',
  ],
  tests_require=[
    'tox',
    'nose',
    'django-nose',
    'coverage',
  ],
)
