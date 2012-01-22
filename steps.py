"""All the dirty work of 'penguin' is here."""

# Toksaitov Dmitrii Alexandrovich
# Tue Nov 8 06:23:02 KGT 2011

import os, multiprocessing, xmlrpclib, time
import utils

class DownloadError(Exception):
    """Exception raised when a download manager failed to get a file."""
    pass

def perform(configuration):
    """Executes all steps to build a system defined in the 'configuration'.

    Partitions the disk, compiles the toolchain, etc.

    """
    device = configuration['device']['path']
    partitions = configuration['partitions']
    root_file_system_device, root_file_system_type = \
            partition_disk(device, partitions)

    mount_point_name = configuration['short name']
    partition_mount_point = '/mnt/%s' % mount_point_name
    mount_root_file_system(root_file_system_device,
                           root_file_system_type,
                           partition_mount_point)

    build_user = configuration.get('build user', None)
    if build_user:
        change_mount_point_owner(partition_mount_point, build_user)
        switch_to_user(build_user)

    adjust_process_environment(partition_mount_point)

    first_build_pass_settings = configuration['first build pass']
    build_toolchain(first_build_pass_settings)

def partition_disk(device, partitions):
    """Tries to partition the 'device' as specified in the list 'partitions'.

    Returns a tuple with the name of the device with the root file system and
    with the type of that system.

    Sample of the list 'partitions':

        [
            {
                "type": "ESP",
                "size": 200
            },
            {
                "type": "BIOS Boot",
                "size": 1
            },
            {
                "type": "Swap",
                "size": 1024
            },
            {
                "type": "Root",
                "file system": "BTRFS"
            }
        ]

    Notes

        The disk layout is set to GPT.

        The EFI System Partition (ESP) and the BIOS Boot partition are created
        with the VFAT file system.

        The size of partition should be specified in binary megabytes. Absence
        of this field means that a particular partition should span the entire
        remaining disk space (excluding several sectors for the secondary GPT
        header and table at the end of the disk).

        The root file system can be ether of type Ext4 or BTRFS.

    """
    utils.stop_if_not_root()
    utils.confirm_disk_destructive_operations(device)

    utils.message('Trying to partition the disk "%s".' % device)

    utils.sh('type parted', 'Checking if GNU parted is installed.')
    utils.sh("parted --script '%s' mklabel gpt" % device,
             'Creating the GPT partition scheme on "%s".' % device)

    device_position = 2

    partitions_specs = {
        'ESP' : [
            'EFI System partition',
            'fat32',
            'boot'
        ],
        'BIOS Boot' : [
            'BIOS Boot partition',
            'fat32',
            'bios_grub'
        ],
        'Swap' : [
            'Swap partition',
            'linux-swap',
            None
        ],
        'Root' : [
            'Linux filesystem data',
            lambda : partition['file system'].lower(),
            None
        ]
    }

    root_file_system_device = root_file_system_type = None

    for partition_number, partition in enumerate(partitions):
        partition_number += 1
        partition_type = partition['type']

        partition_name, partition_file_system, partition_flag = \
            partitions_specs[partition_type]

        if hasattr(partition_file_system, '__call__'):
            partition_file_system = partition_file_system()

        start = "%dMiB" % device_position

        partition_size = partition.get('size', None)
        end = '%dMiB' % (device_position + partition_size) \
                                            if partition_size else '-34s'

        utils.sh('parted --script --align optimal ' \
                 "'%s' \"mkpart '%s' '%s' '%s' '%s'\"" %
                    (device, partition_name, partition_file_system, start, end),
                 'Creating the partition #%d of type "%s" with the name "%s".' %
                    (partition_number, partition_type, partition_name))

        if partition_size:
            device_position += partition_size

        if partition_flag:
            utils.sh("parted --script '%s' set %d '%s' on" %
                        (device, partition_number, partition_flag),
                     'Setting the flag "%s" on the partition #%d.' %
                        (partition_flag, partition_number))

        partition_device = device + str(partition_number)
        if partition_file_system == 'vfat':
            utils.sh('type mkfs.vfat', 'Checking if "mkdosfs" is installed.')
            utils.sh("mkfs.vfat -F 32 '%s'" % partition_device,
                     'Creating the VFAT file system on the device "%s".' %
                        partition_device)
        elif partition_file_system == 'linux-swap':
            utils.sh('type mkswap', 'Checking if the "util-linux" package is ' \
                     'installed and "mkswap" is present.')
            utils.sh("mkswap '%s'" % partition_device,
                     'Setting up the Linux swap partition on the device "%s".' %
                        partition_device)
        elif partition_file_system == 'ext4':
            utils.sh('type mkfs.ext4', 'Checking if the "e2fsprogs" package ' \
                     'is installed and "mkfs.ext4"  is present.')
            utils.sh("mkfs.ext4 '%s'" % partition_device,
                     'Creating the Ext4 file system on device "%s".' %
                        partition_device)
        elif partition_file_system == 'btrfs':
            utils.sh('type mkfs.btrfs', 'Checking if the "btrfs-tools" ' \
                     'package is installed and "mkfs.btrfs" is present.')
            utils.sh("mkfs.btrfs '%s'" % partition_device,
                     'Creating the BTRFS file system on device "%s".' %
                        partition_device)

        # http://developer.apple.com/library/mac/#technotes/tn2166/_index.html
        if partition_type != 'ESP':
            device_position += 128 # Adds space after each partition (excluding
                                   # ESP) for partition managers and other
                                   # system tools.

            if partition_type == 'Root':
                root_file_system_device, root_file_system_type = \
                        partition_device, partition_file_system

    if not root_file_system_device:
        utils.exit('The partition with the root file system was not defined.')

    return (root_file_system_device, root_file_system_type)

def mount_root_file_system(root_file_system_device,
                           root_file_system_type,
                           partition_mount_point):
    """Tries to mount the root file system.

    Tries to mount the 'root_file_system_device' at 'partition_mount_point'.

    """
    utils.sh("mkdir --parents --verbose '%s'" % partition_mount_point,
             'Creating a directory for the root file system mount ' \
             'point at "%s".' % partition_mount_point)
    utils.sh("mount --type '%s' '%s' '%s'" %
                (root_file_system_type,
                 root_file_system_device,
                 partition_mount_point),
             'Mounting the device "%s" at "%s".' %
                (root_file_system_device, partition_mount_point))

def change_mount_point_owner(partition_mount_point, user):
    """Changes the owner and the group of the mount point.

    Changes the owner and the group of 'partition_mount_point' to the value of
    'user'. The group value is set to the current login group of the 'user'.

    """
    uid, gid = utils.get_or_create_user(user)
    utils.sh("chown '%d':'%d' '%s'" % (uid, gid, partition_mount_point),
             'Changing the owner of the mount point "%s" to "%s" (UID: %d, ' \
             'GID: %d).' % (partition_mount_point, user, uid, gid))

def switch_to_user(user):
    """Tries to set the process's user and group IDs to those one of the 'user'.

    If the user is not defined in '/etc/passwd', a new one is created with
    the provided login name.

    The real and effective user and group IDs of the process are affected by
    this operation.

    """
    uid, gid = utils.get_or_create_user(user)
    utils.message("Changing the process's real and effective UID and GID to " \
                  '"%s" (UID: %d, GID: %d).' % (user, uid, gid))

    os.setregid(gid, gid)
    os.setreuid(uid, uid)

def adjust_process_environment(partition_mount_point):
    """Tweaks the process environment for efficient work of its children.

    Sets the current working directory, default user mask, locale, and
    additional flags for 'make'.

    """
    utils.message('Setting the current working directory to the mount point ' \
                  'of the new root partition "%s".' % partition_mount_point)
    os.chdir(partition_mount_point)

    utils.message('Setting the user mask to 022.')
    os.umask(0o022)

    utils.message('Setting the locale to "POSIX".')
    os.environ['LC_ALL'] = 'POSIX'

    cpu_count = multiprocessing.cpu_count()
    if cpu_count > 1:
        utils.message('A multiprocessor system was detected. ' \
                      'Setting the number of jobs the make utility can run ' \
                      'simultaneously to %d.' % cpu_count)
        os.environ['MAKEFLAGS'] = '-j %d' % cpu_count

def build_toolchain(settings):
    """Builds the toolchain to compile the kernel."""

    installation_directory = settings['installation directory']
    package_directory = settings['packages directory']

    if not os.path.isdir(installation_directory):
        utils.sh("mkdir --parents --verbose '%s'" % installation_directory,
                 'Creating the directory for installed toolchain at "%s".' %
                    installation_directory)

    if not os.path.isdir(package_directory):
        utils.sh("mkdir --parents --verbose '%s'" % package_directory,
                 'Creating the directory to store toolchain packages at "%s".' %
                    package_directory)

    initial_working_directories = [os.getcwd()]
    utils.message('Changing the current working directory to "%s".' %
                    package_directory)
    os.chdir(package_directory)

    packages = settings['packages']
    if len(packages) > 0:
        utils.sh('type aria2c', 'Checking if the "aria2" package is ' \
                 'installed "aria2c" is present.')
        utils.sh('aria2c --enable-rpc', 'Starting aria2 - a lightweight ' \
                 'multi-protocol & multi-source download utility.', async=True)
        time.sleep(2)

        aria2 = xmlrpclib.ServerProxy('http://localhost:6800/rpc').aria2

        process_packages(packages, manager=aria2, install=True)

        aria2.shutdown()

def process_packages(packages, manager, install=False):
    """Recursively downloads all 'packages' with a download 'manager' and
       installs them if requested."""

    for package in packages:
        package_source = package['source']
        package_name = package.get('name', package_source)

        utils.message('Trying to get %s.' % package_name)
        download_gid = manager.addUri([package_source])

        while True:
            status = manager.tellStatus(download_gid, ['status'])['status']
            if status == 'complete':
                break
            elif status == 'active':
                time.sleep(1)
            else:
                raise DownloadError

        package_file = manager.getFiles(download_gid)[0]['path']

        package_directory = package.get('directory name', None)
        if package_directory:
            utils.sh("mkdir --parents --verbose '%s'" % package_directory,
                     'Creating the directory "%s" to unpack the package.' %
                        package_directory)
            utils.sh('tar --extract --auto-compress ' \
                     "--strip-components 1 --directory '%s' " \
                     "--file '%s'" % (package_directory, package_file),
                     'Unpacking "%s" into "%s".' %
                        (package_file, package_directory))
        else:
            utils.sh("tar --extract --auto-compress --file '%s'" % package_file,
                     'Unpacking "%s" to the current directory.' % package_file)

        required_packages = package.get('required packages', None)
        if required_packages:
            old_working_directory = os.getcwd()
            if not package_directory:
                parts = package_file.rpartition('.tar')
                package_directory = parts[0] or parts[-1]

            utils.message('Changing the current working directory to "%s".' %
                            package_directory)
            os.chdir(package_directory)

            process_packages(required_packages, manager)

            utils.message('Changing the working directory back to "%s".' %
                            old_working_directory)
            os.chdir(old_working_directory)

