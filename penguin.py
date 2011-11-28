"""Builds custom Linux systems.

Written while on the road of reading Linux From Scratch.

"""

# Toksaitov Dmitrii Alexandrovich
# Fri Nov 4 16:28:03 KGT 2011

import os, signal, sys, traceback
import argparse, json, tempfile

import utils, steps

MAJOR_VERSION, MINOR_VERSION, BUILD_NUMBER = 1, 0, 1

def parse_command_line_arguments():
    """Defines command line arguments and parses the provided one.

    Returns parsed arguments in a dictionary.

    """
    parser = argparse.ArgumentParser(description=__doc__,
                                     fromfile_prefix_chars='@')

    script_version = '%d.%d.%d' % (MAJOR_VERSION, MINOR_VERSION, BUILD_NUMBER)
    parser.add_argument('-v', '--version', action='version',
                        version=('%(prog)s ' + script_version))
    parser.add_argument('-V', '--verbose', action='store_true',
                        help='verbose output from all commands')
    parser.add_argument('-f', '--force', action='store_true',
                        help='confirm all destructive operations')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='be quiet, supress all output')
    parser.add_argument('configuration', nargs=1, type=argparse.FileType('r'),
                        help='JSON configuration file describing a ' \
                             'system to build.')

    parsed_arguments = vars(parser.parse_args())
    return parsed_arguments

def process_command_line_arguments():
    """Processes command-line arguments, constructs and defines script options.

    Returns script options in a dictionary with a system configuration to build.
    System configuration is parsed from the specified JSON file.

    """
    options = parse_command_line_arguments()

    configuration_file = options['configuration'][0]
    options['configuration'] = json.load(configuration_file)
    configuration_file.close()

    utils.verbose_output = options['verbose']
    utils.quiet_mode     = options['quiet']
    utils.forced_mode    = options['force']

    return options

def main():
    """The script entry point"""
    try:
        options = process_command_line_arguments()
        steps.perform(options['configuration'])
    except KeyboardInterrupt:     # Suppress tracebacks on SIGINT
        exit(128 + signal.SIGINT) # http://tldp.org/LDP/abs/html/exitcodes.html
    except Exception as error:
        if __debug__:
            utils.error_message('An error occured.')
            traceback.print_exc()
            utils.exit(1)
        else:
            try:
                temp_file_descriptor, temp_file_path = \
                    tempfile.mkstemp(suffix='.traceback',
                                     prefix='%s.error.' % sys.argv[0],
                                     text=True)
                temp_file = os.fdopen(temp_file_descriptor, 'w')
                traceback.print_exc(file=temp_file)
                temp_file.close()
                utils.exit('Error. %s. The traceback was written ' \
                           'to "%s".' % (error, temp_file_path))
            except Exception:
                utils.exit("Something went completely wrong. %s. And it's " \
                           'not even possible to write the traceback to a ' \
                           'file.' % error)

if __name__ == '__main__':
    main()

