# Utility functions for 'penguin'.
#
# Toksaitov Dmitrii Alexandrovich
# Fri Nov 4 16:28:03 KGT 2011

import subprocess, sys, os

def stop_if_not_root():
    if os.geteuid() != 0:
        sys.exit('This script must be run as root.')

def confirm_destructive_operations():
    confirmation = raw_input('This script will try to repartition the disk '  \
                             'specified in the configuration.\nConfirm that ' \
                             'this is what you want by typing "Continue" '    \
                             'and pressing Enter: ')

    if confirmation.strip() != 'Continue':
        sys.exit(1)

def sh(command, message = None):
    if message:
        print message
    try:
        subprocess.check_output(command, shell = True)
    except Exception as error:
        sys.exit('%s\n%s' % (error.output, error))

