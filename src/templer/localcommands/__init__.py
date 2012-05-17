"""
Package API
"""
from templer.localcommands.command import TemplerLocalCommand
from templer.localcommands.template import TemplerLocalTemplate


SUPPORTS_LOCAL_COMMANDS = True


LOCAL_COMMANDS_MESSAGE = """Your new package supports local commands.  To
access them, change directories into the 'src' directory inside your new
package.  From there, you will be able to run the command `paster add --list`
to see the local commands available for this package.
"""
