"""
ZopeSkel local command.

Most of the code is a copy/paste from paste.script module
"""

import os
import ConfigParser
import pkg_resources
from paste.script import command
from paste.script import pluginlib


class TemplerLocalCommand(command.Command):
    """paster command to add content skeleton to plone project"""

    max_args = 2
    usage = "[template name]"
    summary = "Allows the addition of further templates to an existing package"
    group_name = "Templer local commands"

    parser = command.Command.standard_parser(verbose=True)
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
         self.template_vars['package']) = self.get_parent_namespace_packages()

        dest_dir = self.dest_dir()

        templates = []
        self._extend_templates(templates, args[0])

        templates = [tmpl for name, tmpl in templates]
        for tmpl in templates[::-1]:
            self.template_vars = tmpl.check_vars(self.template_vars, self)

        for tmpl in templates[::-1]:
            if self.verbose:
                print 'Creating template %s' % tmpl.name
            tmpl.run(self, dest_dir, self.template_vars)

    def dest_dir(self):
        ns_pkg, ns_pkg2, pkg = self.get_parent_namespace_packages()
        dest_dir = os.path.join(
            os.path.dirname(pluginlib.find_egg_info_dir(os.getcwd())),
            ns_pkg, ns_pkg2, pkg)
        return dest_dir

    def get_egg_info_dir(self):
        return pluginlib.find_egg_info_dir(os.getcwd())

    def get_namespaces_from_egginfo(self):
        """read the egg-info directory to find our current packages"""
        egg_info = self.get_egg_info_dir()
        hfile = open(os.path.join(egg_info, 'namespace_packages.txt'))
        packages = [l.strip() for l in hfile.readlines()
                    if l.strip() and not l.strip().startswith('#')]
        hfile.close()

        packages.sort(lambda x, y: -cmp(len(x), len(y)))
        namespaces = packages[0].split('.')
        return namespaces

    def get_parent_namespace_packages(self):
        """
        return the project namespaces and package name.
        This method can be a function
        """
        egg_info = self.get_egg_info_dir()
        packages = self.get_namespaces_from_egginfo()
        namespace_package = packages[0]
        namespace_package2 = ''
        if len(packages) == 2:
            namespace_package2 = packages[1]
        (dirpath, dirnames, filenames) = os.walk(os.path.join(
                                            os.path.dirname(egg_info),
                                                    namespace_package,
                                                    namespace_package2)).next()
        # Get the package dir because we usually want to issue the
        # localcommand in the package dir.
        package = os.path.basename(os.path.abspath(os.path.curdir))

        # If the package dir is not in the list of inner_packages,
        # then:
        #    if there is only one package in the list, we take it
        #    else ask the user to pick a package from the list
        inner_packages = [d for d in dirnames if d != '.svn']
        if package not in inner_packages:
            package = inner_packages[0]
            if len(inner_packages) > 1:
                package = self.challenge(
                    'Please choose one package to inject content into %s' %\
                    inner_packages)

        return namespace_package, namespace_package2, package

    def _list_sub_templates(self, show_all=False):
        """
        lists available templates
        """
        templates = []
        parent_template = None

        egg_info_dir = pluginlib.find_egg_info_dir(os.getcwd())
        src_path = os.path.dirname(egg_info_dir)
        setup_path = os.path.sep.join(src_path.split(os.path.sep)[:-1])
        setup_cfg = os.path.join(setup_path, 'setup.cfg')

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
                   parent_template is None or \
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
