"""
ZopeSkel local command.

Most of the code is a copy/paste from paste.script module
"""

import os
import ConfigParser
import pkg_resources
from templer.core.create import Command
from templer.core import pluginlib


class TemplerLocalCommand(Command):
    """paster command to add content skeleton to plone project"""

    max_args = 2
    usage = "[template name]"
    summary = "Allows the addition of further templates to an existing package"
    group_name = "Templer local commands"

    parser = Command.standard_parser(verbose=True)
    parser.add_option(
        '-l', '--list',
        action='store_true',
        dest='listcontents',
        help="List available templates for the current project")

    parser.add_option(
        '-a', '--list-all',
        action='store_true',
        dest='listallcontents',
        help="List all templates regardless of the current project")

    parser.add_option(
        '-q', '--no-interactive',
        action="count",
        dest="no_interactive",
        default=0)

    template_vars = {}

    def __init__(self, command_name):
        self.command_name = command_name

    def command(self):
        """
        command method
        """
        self.interactive = 1
        options, args = self.options, self.args

        if options.listcontents:
            self._list_sub_templates()
            return

        if options.listallcontents:
            self._list_sub_templates(show_all=True)
            return

        if options.no_interactive:
            self.interactive = False

        if len(args) < 1:
            print "\n\tError: Need a template name\n"
            return

        (self.template_vars['namespace_package'],
         self.template_vars['namespace_package2'],
         self.template_vars['package'],
         dest_dir) = self.get_parent_namespace_packages()

        templates = []
        self._extend_templates(templates, args[0])

        templates = [tmpl for name, tmpl in templates]
        for tmpl in templates[::-1]:
            self.template_vars = tmpl.check_vars(self.template_vars, self)

        for tmpl in templates[::-1]:
            if self.verbose:
                print 'Creating template %s' % tmpl.name
            tmpl.run(self, dest_dir, self.template_vars)

    def get_parent_namespace_packages(self):
        """
        return the project namespaces and package name.
        This method can be a function
        """
        namespace_package = ''
        namespace_package2 = ''
        packages = []
        # Find Python packages (identified by __init__.py)
        base_path = os.getcwd()
        for dirpath, dirnames, filenames in os.walk(os.getcwd()):
            if '__init__.py' in filenames:
                init_py = os.path.join(dirpath, '__init__.py')
                basename = os.path.basename(dirpath)
                # Heuristic to identify namespace packages
                if 'declare_namespace' in open(init_py).read():
                    if not namespace_package:
                        namespace_package = basename
                        base_path = dirpath
                    elif not namespace_package2:
                        namespace_package2 = basename
                        base_path = dirpath
                else:
                    # Build a list of all non-namespace packages,
                    # except for ones contained in another
                    # non-namespace package. This includes e.g.
                    # foo.bar but not foo.bar.tests, if foo is
                    # the namespace.
                    if os.path.relpath(os.path.dirname(dirpath), base_path) in packages:
                        continue
                    packages.append(os.path.relpath(dirpath, base_path))

        # If more than one package is included in this distribution,
        # make the user pick.
        package = packages[0]
        if len(packages) > 1:
            package = self.challenge(
                'Please choose one package to inject content into %s' %\
                packages)

        if namespace_package2:
            subpath = "%s/%s/%s" % \
                (namespace_package, namespace_package2, package)
        else:
            subpath = "%s/%s" % (namespace_package, package)
        destination = os.path.abspath(subpath)

        return namespace_package, namespace_package2, package, destination

    def _list_sub_templates(self, show_all=False):
        """
        lists available templates
        """
        templates = []
        parent_template = None

        setup_cfg = os.path.join(os.path.dirname(os.getcwd()), 'setup.cfg')

        parent_template = None
        if os.path.exists(setup_cfg):
            parser = ConfigParser.ConfigParser()
            parser.read(setup_cfg)
            try:
                parent_template =\
                    parser.get('templer.local', 'template') or None
            except:
                pass

        for entry in self._all_entry_points():
            try:
                entry_point = entry.load()
                t = entry_point(entry.name)
                if show_all or \
                   parent_template in t.parent_templates:
                    templates.append(t)
            except Exception, e:
                # We will not be stopped!
                print 'Warning: could not load entry point %s (%s: %s)' % (
                    entry.name, e.__class__.__name__, e)

        print 'Available templates:'
        if not templates:
            print '  No template'
            return

        max_name = max([len(t.name) for t in templates])
        templates.sort(lambda a, b: cmp(a.name, b.name))

        for template in templates:
            _marker = " "
            if not template.parent_templates:
                _marker = '?'
            elif parent_template not in template.parent_templates:
                _marker = 'N'

            # @@: Wrap description
            print '  %s %s:%s  %s' % (
                _marker,
                template.name,
                ' '*(max_name-len(template.name)),
                template.summary)

    def _all_entry_points(self):
        """
        Return all entry points under templer.templer_sub_template
        """
        if not hasattr(self, '_entry_points'):
            self._entry_points = list(pkg_resources.iter_entry_points(
            'templer.templer_sub_template'))
        return self._entry_points

    def _extend_templates(self, templates, tmpl_name):
        """
        Return ...
        """
        if '#' in tmpl_name:
            dist_name, tmpl_name = tmpl_name.split('#', 1)
        else:
            dist_name, tmpl_name = None, tmpl_name
        if dist_name is None:
            for entry in self._all_entry_points():
                if entry.name == tmpl_name:
                    tmpl = entry.load()(entry.name)
                    dist_name = entry.dist.project_name
                    break
            else:
                raise LookupError(
                    'Template by name %r not found' % tmpl_name)
        else:
            dist = pkg_resources.get_distribution(dist_name)
            entry = dist.get_entry_info(
                'paste.paster_create_template', tmpl_name)
            tmpl = entry.load()(entry.name)
        full_name = '%s#%s' % (dist_name, tmpl_name)
        for item_full_name, in templates:
            if item_full_name == full_name:
                # Already loaded
                return
        for req_name in tmpl.required_templates:
            self._extend_templates(templates, req_name)
        templates.append((full_name, tmpl))
