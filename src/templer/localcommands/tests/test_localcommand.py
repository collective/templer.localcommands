import os
import shutil
import sys
import tempfile
import unittest2 as unittest
import StringIO

from templer.core.control_script import Runner
from templer.core.tests.test_templates import read_sh
from templer.core.tests.test_templates import templer as templercmd
from templer.core.tests.test_templates import clean_working_set
from templer.localcommands import TemplerLocalCommand


def capture_output(command, *args, **kwargs):
    oldout = sys.stdout
    newout = StringIO.StringIO()
    sys.stdout = newout
    command(*args, **kwargs)
    sys.stdout = oldout
    return newout.getvalue()


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

    def test_add_list_option(self):
        """verify that the --list option works properly

        It should print that no commands are available if none are, or 
        list the available local commands if some are.
        """
        self.fail('must write this test')

    def test_add_list_all_option(self):
        """verify that the --list-all (-a) option works properly
        
        It should list all localcommands regardless of their availability in
        the current context.
        """
        self.fail('must write this test')

    def test_add_no_locals_available(self):
        """verify that the add command fails gracefully when no localcommands
        are available in the current context
        """
        self.fail('must write this test')

    def test_add_available_with_package(self):
        """verify that within a supporting package, add is available"""
        # XXX we should create a local command just for testing,
        # rather than assuming templer.plone.localcommands is present
        templercmd(" ".join(self.options))
        os.chdir('plone.example')
        # we must re-initialize the runner so it can be context aware
        newrunner = Runner()
        templercmd('add portlet --no-interactive', runner=newrunner)
        home_path = os.path.join('src', 'plone', 'example')
        self.assertTrue('portlets' in os.listdir(home_path))

    def test_get_parent_namespace_packages(self):
        """verify that the current namespace package(s) can be determined"""
        templercmd(" ".join(self.options))
        os.chdir(os.path.sep.join(['plone.example', 'src']))
        # this should return a list of namespace packages
        namespaces = self.local_cmd.get_parent_namespace_packages()
        expected = ('plone', '', 'example', 'plone.example/src/plone/example')
        self.assertEqual(len(namespaces), len(expected))
        for idx, node in enumerate(expected):
            found = namespaces[idx]
            self.assertTrue(found.endswith(node))
