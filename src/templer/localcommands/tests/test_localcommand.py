import os
import shutil
import tempfile
import unittest2 as unittest

from templer.core.tests.test_templates import read_sh
from templer.core.tests.test_templates import templer
from templer.core.tests.test_templates import clean_working_set
from templer.localcommands import TemplerLocalCommand


class TestLocalCommands(unittest.TestCase):
    """exercise the functions of the TemplerLocalCommand class"""

    def setUp(self):
        """create a temporary directory, cd to it for the duration of the test
        """
        self.orig_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        # TODO: I am bothered by the fact that this depends on infrastructure
        # built by the buildout for this package.  If the dev environment is
        # different in some way, this is very brittle.  Is there a way to
        # make the 'templer' shell script available to be run in a shell like
        # we are using it below?
        cmdpath = ['bin', 'templer']
        cmdpath[:0] = self.orig_dir.split(os.path.sep)
        self.cmd = os.path.sep.join(cmdpath)
        self.options = [
            'plone_basic', 'plone.example', '--no-interactive']
        os.chdir(self.temp_dir)
        self.local_cmd = TemplerLocalCommand("My_Command")

    def tearDown(self):
        """cd back home, remove the temporary directory created for this test
        """
        os.chdir(self.orig_dir)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None
        clean_working_set()

    def test_add_not_generally_available(self):
        result = read_sh(self.cmd + ' add foo')
        self.fail('We need to fail more gracefully here.')

    def test_add_available_with_package(self):
        """verify that within a supporting package, add is available"""
        # XXX we should create a local command just for testing,
        # rather than assuming templer.plone.localcommands is present
        templer(" ".join(self.options))
        os.chdir(os.path.sep.join(['plone.example', 'src']))
        templer('add portlet --no-interactive')
        self.assertTrue('portlets' in os.listdir('example'))

    def test_get_parent_namespace_packages(self):
        """verify that the current namespace package(s) can be determined"""
        templer(" ".join(self.options))
        os.chdir(os.path.sep.join(['plone.example', 'src']))
        # this should return a list of namespace packages
        namespaces = self.local_cmd.get_parent_namespace_packages()
        expected = ('plone', '', 'example', 'plone.example/src/plone/example')
        self.assertEqual(len(namespaces), len(expected))
        for idx, node in enumerate(expected):
            found = namespaces[idx]
            self.assertTrue(found.endswith(node))
