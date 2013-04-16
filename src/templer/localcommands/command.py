"""
Templer local command.

Most of the code is a copy/paste from paste.script module
"""

import os
import ConfigParser
import pkg_resources
from templer.core.create import Command


NOT_LOCAL_CONTEXT_WARNING = """
You have invoked the 'add' command, which runs localcommands, but you are not
in a context where this is appropriate.  

If you have just generated a new package which supports localcommands, change
directories so that you are in the same location as the ``setup.py`` file
for that package and try again
"""
NO_TEMPLATE_SUPPORTED_WARNING = """
You have invoked the 'add' command, which runs localcommands, but the '%s'
template used to generate this package does not support any localcommands.
"""
TEMPLATE_NOT_SUPPORTED_WARNING = """
You have invoked the 'add' command, requesting the '%s' localcommand, but that
localcommand is not supported by the '%s' template, which was used to create
this package.

To see a list of supported localcommands, please invoke the 'add' command with
the '--list' or '-l' option:

    $ templer add -l
"""
LOCALCOMMAND_LISTING_HEADER = "Available Templates:"
NO_COMMANDS_AVAILABLE = "    None available in this context"
AVAILABLE_MARKER = " "
UNAVAILABLE_MARKER = "N"
UNKNOWN_MARKER = "?"


class TemplerLocalCommand(Command):
    """a command which supports extending a previously created template
    """
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
        self.parent_template = self._get_parent_template()

    def command(self):
        """
        command method
        """
        if self.parent_template is None:
            # if there is no parent_template, we are not in an appropriate
            # context, message the user and return with return_code 1
            self.return_code = 1
            print NOT_LOCAL_CONTEXT_WARNING
            return
            
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
            self.return_code = 1
            print "\n\tError: Need a template name\n"
            return

        (self.template_vars['namespace_package'],
         self.template_vars['namespace_package2'],
         self.template_vars['package'],
         dest_dir) = self.get_parent_namespace_packages()

        templates = []
        self._extend_templates(templates, args[0], first=True)

        # if, after estending the templates we have no templates to run, then
        # we are in a local context, but the template requested is not 
        # supported by our parent_template.  message the user and return with
        # return_code = 1
        if not templates:
            self.return_code = 1
            # Are any templates at all supported by this parent?
            if not self._get_sub_templates():
                print NO_TEMPLATE_SUPPORTED_WARNING % self.parent_template
            else:
                print TEMPLATE_NOT_SUPPORTED_WARNING % (args[0],
                                                        self.parent_template)
            return

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

        destination = os.path.join(base_path, package)

        return namespace_package, namespace_package2, package, destination

    def _get_parent_template(self):
        """read the parent template for this package from setup.cfg

        if setup.cfg is absent, or missing the required info, return None
        """
        parent_template = None
        # this is clumsy and inflexible.  It'd be nice to be able to walk 
        # up from any location inside a package rather than requiring you 
        # to be where the setup.cfg file is.
        setup_cfg = os.path.join(os.getcwd(), 'setup.cfg')
        if os.path.exists(setup_cfg):
            parser = ConfigParser.ConfigParser()
            parser.read(setup_cfg)
            try:
                parent_template =\
                    parser.get('templer.local', 'template') or None
            except:
                pass
        return parent_template

    def _get_sub_templates(self, get_all=False):
        templates = []

        for entry in self._all_entry_points():
            try:
                entry_point = entry.load()
                t = entry_point(entry.name)
                if get_all or self.parent_template in t.parent_templates:
                    templates.append(t)
            except Exception, e:
                # We will not be stopped!
                print 'Warning: could not load entry point %s (%s: %s)' % (
                    entry.name, e.__class__.__name__, e)
        return templates

    def _list_sub_templates(self, show_all=False):
        """
        lists available templates
        """
        templates = self._get_sub_templates(get_all=show_all)

        print LOCALCOMMAND_LISTING_HEADER
        if not templates:
            print NO_COMMANDS_AVAILABLE
            return

        max_name = max([len(t.name) for t in templates])
        templates.sort(lambda a, b: cmp(a.name, b.name))

        for template in templates:
            _marker = AVAILABLE_MARKER
            if not template.parent_templates:
                _marker = UNKNOWN_MARKER
            elif self.parent_template not in template.parent_templates:
                _marker = UNAVAILABLE_MARKER

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

    def _extend_templates(self, templates, tmpl_name, first=None):
        """
        recursively build the list of templates that must be run
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

        # if this is the first time through the loop, we need to check if the
        # parent template of this run is in the list of parent templates. If
        # not then we proceed no further.
        if first:
            if self.parent_template not in tmpl.parent_templates:
                return

        for req_name in tmpl.required_templates:
            self._extend_templates(templates, req_name)
        templates.append((full_name, tmpl))
