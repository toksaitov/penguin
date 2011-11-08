"""Utility functions for 'penguin'"""

# Toksaitov Dmitrii Alexandrovich
# Fri Nov 4 16:28:03 KGT 2011

import subprocess, sys, os

verbose_output = False

def stop_if_not_root():
    """Checks whether the script is executed under the root user.

    Exits with the error code 1 if the script is not executed under the root
    user.

    """
    if os.geteuid() != 0:
        sys.exit('This script must be run as root.')

def confirm_disk_destructive_operations():
    """Asks the user to confirm destructive disk operations.

    Otherwise exits with code 1.

    """
    confirmation = raw_input('''This script will try to repartition the disk
                                specified in the configuration.\nConfirm that
                                this is what you want by typing "Continue"
                                and pressing Enter: ''')

    if confirmation.strip() != 'Continue':
        sys.exit(1)

def sh(command, message=None):
    """Prints a message if provided and executes a command in a subshell.

    If the command was unsuccessful, prints its output and the error message and
    exits with the code 1.

    If the command was successful and the verbose mode was turned on, prints the
    command output.

    """
    if message:
        print message
    try:
        output = subprocess.check_output(command, shell=True)
        if verbose_output: print output
    except Exception as error:
        sys.exit('%s\n%s' % (error.output, error))

