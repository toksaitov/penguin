"""Builds custom Linux systems.

Written while on the road of reading "Linux From Scratch".

"""

# Toksaitov Dmitrii Alexandrovich
# Fri Nov 4 16:28:03 KGT 2011

import argparse, json, os, sys, traceback, tempfile
import steps

MAJOR_VERSION, MINOR_VERSION, BUILD_NUMBER = 1, 0, 1

def parse_command_line_arguments():
    """Defines command line arguments and parses provided one.

    Returns parsed arguments in a dictionary.

    """
    parser = argparse.ArgumentParser(description=__doc__,
                                     fromfile_prefix_chars='@')

    script_version = '%d.%d.%d' % (MAJOR_VERSION, MINOR_VERSION, BUILD_NUMBER)
    parser.add_argument('-V', '--version', action='version',
                        version=('%(prog)s ' + script_version))
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose output from all commands')
    parser.add_argument('configuration', nargs=1, type=argparse.FileType('r'),
                        help='a JSON file with description of a ' \
                             'system to build.')

    parsed_arguments = vars(parser.parse_args())
    return parsed_arguments

def process_command_line_arguments():
    """Processes command-line arguments and constructs script options from them.

    Returns script options in a dictionary with a system configuration to build.
    System configuration in JSON is parsed from the specified (through
    command-line) file.

    """
    parsed_arguments = parse_command_line_arguments()

    configuration_file = parsed_arguments['configuration'][0]
    configuration = json.load(configuration_file)
    configuration_file.close()

    options = { 'verbose_output' : parsed_arguments['verbose'],
                'configuration'  : configuration }

    return options

def main():
    """The script entry point"""
    try:
        options = process_command_line_arguments()
        steps.perform(options)
    except Exception:
        if __debug__:
            traceback.print_exc()
            sys.exit(1)
        else:
            try:
                temp_file_descriptor, temp_file_path = \
                    tempfile.mkstemp(suffix='.traceback',
                                     prefix='%s.error.' % sys.argv[0],
                                     text=True)
                temp_file = os.fdopen(temp_file_descriptor, 'w')
                traceback.print_exc(file=temp_file)
                temp_file.close()
                sys.exit('Something went wrong. The traceback was written to ' \
                         '"%s".' % temp_file_path)
            except Exception:
                sys.exit("Something went completely wrong. It's not even " \
                         'possible to write the traceback to a file.')

if __name__ == '__main__':
    main()

