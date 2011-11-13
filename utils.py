"""Utility functions for 'penguin'"""

# Toksaitov Dmitrii Alexandrovich
# Fri Nov 4 16:28:03 KGT 2011

from __future__ import print_function

import subprocess, sys, os

verbose_output = False
quiet_mode     = False

def exit(code=0, message=None):
    """'exit' procedure that honors the quiet mode.

    Calls sys.exit, passes it the provided message unless the quiet mode is on.

    """
    if quiet_mode or not message:
        sys.exit(code)
    else:
        sys.exit(message)

def stop_if_not_root():
    """Checks whether the script is executed under the root user.

    Exits with the error code 1 if the script is not executed under the root
    user.

    """
    if os.geteuid() != 0:
        exit('This script must be run as root.')

def message(content):
    """Prints the content of the message if the quiet mode is not on."""

    if not quiet_mode:
        print(content)

def error_message(message):
    """Prints the message to standard error if the quiet mode is not on."""

    if not quiet_mode:
        print(message, file=sys.stderr)

def sh(command, explanation=None):
    """Prints the explanation if provided and executes a command in a subshell.

    If the command was unsuccessful, prints its output and the error message and
    exits with the error code 1.

    If the command was successful and the verbose mode was turned on, prints the
    command output.

    """
    if explanation:
        message(explanation)
    try:
        if verbose_output:
            if quiet_mode:
                stdout = stderr = open(os.devnull, 'w')
            else:
                stdout, stderr = sys.stdout, sys.stderr
            subprocess.check_call(command, stdout=stdout,
                                           stderr=stderr,
                                           shell=True)
        else:
            subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as error:
        if hasattr(error, 'output'):
            exit('%s\n%s' % (error.output, error))
        else:
            exit(error)

