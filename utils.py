"""Utility functions for 'penguin'"""

# Toksaitov Dmitrii Alexandrovich
# Fri Nov 4 16:28:03 KGT 2011

from __future__ import print_function

import subprocess, sys, os

verbose_output = False
forced_mode    = False
quiet_mode     = False

def exit(code=0, message=None):
    """An exit procedure that honors the quiet mode.

    Calls sys.exit, passes it the provided 'message' unless the quiet mode is on.
    If quiet mode is on or the message was not provided, calls sys.exit passing
    it the exit 'code'.

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

def confirm_disk_destructive_operations(device):
    """Asks the user to confirm destructive operations on the specified 'device'.

    ...otherwise exits with code 1.

    If the forced mode is on, no questions are asked.

    """
    if not forced_mode:
        confirmation = raw_input('This script will try to repartition the ' \
                                 'disk "%s".\n'                             \
                                 'Confirm that this is what you want by '   \
                                 'typing "Continue" and pressing Enter: ' %
                                    device)

        if confirmation.strip() != 'Continue':
            exit(1)

def message(content):
    """Prints the 'content' of the message if the quiet mode is not on."""

    if not quiet_mode:
        print(content)

def error_message(message):
    """Prints the 'message' to standard error if the quiet mode is not on."""

    if not quiet_mode:
        print(message, file=sys.stderr)

def sh(command, explanation=None):
    """Prints the 'explanation', if provided, and executes the 'command'.

    If the 'command' was unsuccessful, prints its output and the error message
    and exits with the error code 1.

    If the 'command' was successful and the verbose mode was turned on, prints
    the 'command' output.

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

def get_or_create_user(user):
    """Gets the UID/GID of the 'user' or creates a new 'user' if it does not exist.

    Returns a tuple with the UID and GID of the 'user'.

    """
    uid, gid = get_user_uid_and_gid(user)
    if not uid:
        sh("useradd -M -U '%s'" % user, 'Creating the build user ' \
           '"%s" and its group.' % user)

    uid, gid = get_user_uid_and_gid(user)
    if not uid or not gid:
        exit("Failed to create the build user.")

    return (uid, gid)

def get_user_uid_and_gid(user):
    """Searches for UID and GID of the 'user' in '/etc/passwd'.

    Returns a tuple containing the UID and GID. If a certain ID was not found,
    its value in the tuple is returned as 'None'.

    """
    uid = gid = None

    with open('/etc/passwd', 'r') as password_file:
        for line in password_file:
            fields = line.split(':')
            if fields[0] == user:
                uid, gid = [int(field) for field in fields[2:4]]
                break

    return (uid, gid)

