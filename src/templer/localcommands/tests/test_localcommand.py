import os
import shutil
import sys
import tempfile
import unittest2 as unittest
import StringIO
import pkg_resources

from templer.core.control_script import Runner
from templer.core.tests.test_templates import read_sh
from templer.core.tests.test_templates import templer as templercmd
from templer.core.tests.test_templates import clean_working_set
from templer.core.vars import var
from templer.core.basic_namespace import BasicNamespace
from templer.localcommands import TemplerLocalTemplate
from templer.localcommands import TemplerLocalCommand
from templer.localcommands.command import NOT_LOCAL_CONTEXT_WARNING
from templer.localcommands.command import TEMPLATE_NOT_SUPPORTED_WARNING
from templer.localcommands.command import NO_TEMPLATE_SUPPORTED_WARNING


class ModuleLocalCommand(TemplerLocalTemplate):
    """A bogus local command for use in testing"""
    use_cheetah = True
    parent_templates = ['basic_namespace', ]

    _template_dir = 'templates/module'

    vars = [
      var('module_name', 'Module Name',  default="mymodule"), ]


MOCK_EP = """
module = templer.localcommands.tests.test_localcommand:ModuleLocalCommand
"""


class TestRunningLocalCommands(unittest.TestCase):
    """Test run-time operation of localcommands"""

    def setUp(self):
        """create a temporary directory, cd to it for the duration of the test
        """
        self.orig_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        self.dist = pkg_resources.get_distribution('templer.localcommands')
        self._add_mock_localcommand(self.dist)
        self.options = [
            'basic_namespace', 'testing.example', '--no-interactive']
        os.chdir(self.temp_dir)

    def tearDown(self):
        """cd back home, remove the temporary directory created for this test
        """
        os.chdir(self.orig_dir)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None
        clean_working_set()
        self._remove_mock_localcommand(self.dist)

    def _add_mock_localcommand(self, dist):
        """set up a fake entry point for the duration of this test
        """
        self.old_ep_map = dist.get_entry_map()
        new_ep_map = self.old_ep_map.copy()
        new_ep_map['templer.templer_sub_template'] = {
            'module': pkg_resources.EntryPoint.parse(MOCK_EP, dist=dist)
        }
        dist._ep_map = new_ep_map
        # in addition, the basic namespace class should use_local_commands
        BasicNamespace.use_local_commands = True

    def _remove_mock_localcommand(self, dist):
        """destroy the fake entry point created for this test
        """
        dist._ep_map = self.old_ep_map.copy()
        del self.old_ep_map
        # and finally, return BasicNamespace to original status
        BasicNamespace.use_local_commands = False

    # def test_add_list_option_templates_available(self):
    #     """verify that the --list option works properly
    # 
    #     It should print that no commands are available if none are, or 
    #     list the available local commands if some are.
    #     """
    #     self.fail('must write this test')
    # 
    # def test_add_list_option_templates__not_available(self):
    #     """verify that the --list option works properly
    # 
    #     It should print that no commands are available if none are, or 
    #     list the available local commands if some are.
    #     """
    #     self.fail('must write this test')
    # 
    # def test_add_list_all_option(self):
    #     """verify that the --list-all (-a) option works properly
    #     
    #     It should list all localcommands regardless of their availability in
    #     the current context.
    #     """
    #     self.fail('must write this test')

    def test_add_not_in_context(self):
        actual = templercmd("add module --no-interactive", silent=True)
        expected = NOT_LOCAL_CONTEXT_WARNING
        self.assertTrue(expected in actual)
    
    def test_add_no_locals_available(self):
        """verify that the add command fails gracefully when no localcommands
        are available in the current context
        """
        options = ['nested_namespace', 'testing.nested.example',
                   '--no-interactive']
        templercmd(" ".join(options), silent=True)
        os.chdir('testing.nested.example')
        actual = templercmd("add module --no-interactive", silent=True)
        expected = NO_TEMPLATE_SUPPORTED_WARNING % 'nested_namespace'
        self.assertTrue(expected in actual)
    
    def test_add_available_with_package(self):
        """verify that within a supporting package, add is available"""
        templercmd(" ".join(self.options), silent=True)
        os.chdir('testing.example')
        # we must re-initialize the runner so it can be context aware
        newrunner = Runner()
        templercmd('add module --no-interactive',
                   runner=newrunner, silent=True)
        home_path = os.path.join('src', 'testing', 'example')
        self.assertTrue('mymodule' in os.listdir(home_path))


class TestLocalCommandFunctions(unittest.TestCase):

    def setUp(self):
        """create a temporary directory, cd to it for the duration of the test
        """
        self.orig_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        self.local_cmd = TemplerLocalCommand('MyCommand')
        self.options = [
            'basic_namespace', 'testing.example', '--no-interactive']
        os.chdir(self.temp_dir)

    def tearDown(self):
        """cd back home, remove the temporary directory created for this test
        """
        os.chdir(self.orig_dir)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None
        clean_working_set()
    
    def test_get_parent_namespace_packages(self):
        """verify that the current namespace package(s) can be determined"""
        templercmd(" ".join(self.options), silent=True)
        os.chdir(os.path.sep.join(['testing.example', 'src']))
        # this should return a list of namespace packages
        namespaces = self.local_cmd.get_parent_namespace_packages()
        expected = ('testing', '', 'example',
                    'testing.example/src/testing/example')
        self.assertEqual(len(namespaces), len(expected))
        for idx, node in enumerate(expected):
            found = namespaces[idx]
            self.assertTrue(found.endswith(node))
