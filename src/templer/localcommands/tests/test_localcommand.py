import os
import re
import shutil
import sys
import tempfile
import unittest2 as unittest

from templer.core.tests.test_templates import read_sh
from templer.core.tests.test_templates import paster
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
        # make the 'paster' shell script available to be run in a shell like
        # we are using it below?
        cmdpath = ['bin', 'paster']
        cmdpath[:0] = self.orig_dir.split(os.path.sep)
        self.cmd = os.path.sep.join(cmdpath)
        self.options = [
            'create', '-t', 'plone_basic', 'plone.example', '--no-interactive']
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
        cmd_pattern = r"^\s*add"
        help_text = read_sh(self.cmd + ' help')
        matches = re.search(cmd_pattern, help_text, re.I|re.M)
        self.assertEquals(matches, None, "add command should not be present")

    def test_add_available_with_package(self):
        """verify that within a supporting package, add is available"""
        paster(" ".join(self.options))
        # I would expect this to work too, but it does not, why?:
        # command_output = read_sh(self.cmd + " " + " ".join(self.options))
        # expected = 'Your new package supports local commands'
        # self.assertTrue(expected in command_output)
        os.chdir(os.path.sep.join(['plone.example', 'src']))
        cmd_pattern = r"^\s*add"
        help_text = read_sh(self.cmd + ' help')
        matches = re.search(cmd_pattern, help_text, re.I|re.M)
        self.assertTrue(matches is not None, 'add command should be present')

    def test_get_namespaces_from_egginfo(self):
        """verify that the current namespace package(s) can be determined"""
        paster(" ".join(self.options))
        os.chdir(os.path.sep.join(['plone.example', 'src']))
        # this should return a list of namespace packages
        namespaces = self.local_cmd.get_namespaces_from_egginfo()
        self.assertTrue('plone' in namespaces)

    def test_dest_dir(self):
        """verify the coorect destination directory for template generation"""
        paster(" ".join(self.options))
        os.chdir(os.path.sep.join(['plone.example', 'src']))
        dest_dir = self.local_cmd.dest_dir()
        expected = os.path.sep.join(['plone.example', 'src',
                                     'plone', 'example'])
        self.assertTrue(dest_dir.endswith(expected))
