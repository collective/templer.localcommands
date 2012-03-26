import os
import subprocess

from paste.script import templates
from paste.script import copydir


class TemplerLocalTemplate(templates.Template):
    """
    Base template class
    """

    marker_name = "extra stuff goes here"
    #list of templates this subtemplate is related to
    parent_templates = []

    def run(self, command, output_dir, vars):
        """
        the run method
        """
        (vars['namespace_package'],
         vars['namespace_package2'],
         vars['package']) = command.get_parent_namespace_packages()

        if vars['namespace_package2']:
            vars['package_dotted_name'] = "%s.%s.%s" % \
                (vars['namespace_package'],
                vars['namespace_package2'],
                vars['package'])
        else:
            vars['package_dotted_name'] = "%s.%s" % \
                (vars['namespace_package'],
                 vars['package'])

        self.pre(command, output_dir, vars)
        self.write_files(command, output_dir, vars)
        self.post(command, output_dir, vars)

    def write_files(self, command, output_dir, vars):
        """
        method
        """
        self._command = command
        template_dir = self.template_dir()
        if not os.path.exists(output_dir):
            print "Creating directory %s" % output_dir
            if not command.simulate:
                # Don't let copydir create this top-level directory,
                # since copydir will svn add it sometimes:
                os.makedirs(output_dir)
        self.copy_dir(template_dir, output_dir,
                         vars,
                         verbosity=1,
                         simulate=0,
                         interactive=1,
                         overwrite=0,
                         indent=1,
                         use_cheetah=self.use_cheetah,
                         template_renderer=self.template_renderer)

    def copy_dir(self, source, dest, vars, verbosity, simulate, indent=0,
                 use_cheetah=False, sub_vars=True, interactive=False,
                 svn_add=True, overwrite=True, template_renderer=None):
        """
        This method is a modified copy of paste.script.copy_dir
        """
        # This allows you to use a leading +dot+ in filenames which would
        # otherwise be skipped because leading dots make the file hidden:
        vars.setdefault('dot', '.')
        vars.setdefault('plus', '+')
        names = os.listdir(source)
        names.sort()
        pad = ' '*(indent*2)
        if not os.path.exists(dest):
            if verbosity >= 1:
                print '%sCreating %s/' % (pad, dest)
            if not simulate:
                copydir.svn_makedirs(dest, svn_add=svn_add,
                                     verbosity=verbosity, pad=pad)
        elif verbosity >= 2:
            print '%sDirectory %s exists' % (pad, dest)
        for name in names:
            full = os.path.join(source, name)
            reason = copydir.should_skip_file(name)
            if reason:
                if verbosity >= 2:
                    reason = pad + reason % {'filename': full}
                    print reason
                continue

            if sub_vars:
                dest_full = os.path.join(
                    dest, copydir.substitute_filename(name, vars))
            sub_file = False
            if dest_full.endswith('_tmpl'):
                dest_full = dest_full[:-5]
                sub_file = sub_vars
            if os.path.isdir(full):
                if verbosity:
                    print '%sRecursing into %s' % (pad, os.path.basename(full))
                self.copy_dir(full, dest_full, vars, verbosity, simulate,
                         indent=indent+1, use_cheetah=use_cheetah,
                         sub_vars=sub_vars, interactive=interactive,
                         svn_add=svn_add, template_renderer=template_renderer)
                continue
            f = open(full, 'rb')
            content = f.read()
            f.close()
            try:
                content = copydir.substitute_content(
                    content,
                    vars,
                    filename=full,
                    use_cheetah=use_cheetah,
                    template_renderer=template_renderer)
            except copydir.SkipTemplate:
                continue

            if dest_full.endswith('_insert'):
                dest_full = dest_full[:-7]

            already_exists = os.path.exists(dest_full)
            if already_exists:
                if sub_file and verbosity:
                    print "File '%s' already exists: skipped" % \
                           os.path.basename(dest_full)
                    continue
                f = open(dest_full, 'rb')
                old_content = f.read()
                f.close()
                if old_content == content:
                    if verbosity:
                        print '%s%s already exists (same content)' % \
                               (pad, dest_full)
                    continue

                if verbosity:
                    print "%sInserting from %s into %s" % \
                                (pad, os.path.basename(full), dest_full)

                if not content.endswith('\n'):
                    content += '\n'
                # remove lines starting with '#'
                content = '\n'.join([l for l in content.split('\n') \
                                     if not l.startswith('#')])
                self._command.insert_into_file(dest_full,
                                               self.marker_name,
                                               content)
                continue

            if verbosity:
                print '%sCopying %s to %s' % (pad,
                                              os.path.basename(full),
                                              dest_full)
            # remove '#' from the start of lines
            if not sub_file:
                content = content.replace('\n#', '\n')
                if content[0] == '#': 
                    content = content[1:]

            if not simulate:
                f = open(dest_full, 'wb')
                f.write(content)
                f.close()
            if svn_add and not already_exists:
                if not os.path.exists(
                           os.path.join(
                               os.path.dirname(
                                   os.path.abspath(dest_full)), '.svn')):
                    if verbosity > 1:
                        print '%s.svn/ does not exist; cannot add file' % pad
                else:
                    cmd = ['svn', 'add', dest_full]
                    if verbosity > 1:
                        print '%sRunning: %s' % (pad, ' '.join(cmd))
                    if not simulate:
                        # @@: Should
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                        stdout, stderr = proc.communicate()
                        if verbosity > 1 and stdout:
                            print 'Script output:'
                            print stdout
            elif svn_add and already_exists and verbosity > 1:
                print '%sFile already exists (not doing svn add)' % pad
