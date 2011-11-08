"""All dirty work of 'penguin' is here."""

# Toksaitov Dmitrii Alexandrovich
# Tue Nov 8 06:23:02 KGT 2011

from utils import *

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

def perform(options):
    """Executes all steps to build a system.

    Partitions the disk, compiles the toolchain, etc.

    """
    global verbose_output
    verbose_output = options.verbose_output

    partition_disk(options.configuration)

def partition_disk(configuration):
    """Tries to partition the disk as specified in the configuration file.

    Samples of required fields in a JSON configuration:

        {
            "short name" : "some-name",

            "device" : {
                "path"   : "/dev/sdb",
            },

            "partitions" : [
                {
                    "type" : "ESP",
                    "size" : 200
                },
                {
                    "type" : "BIOS Boot",
                    "size" : 1
                },
                {
                    "type" : "Swap",
                    "size" : 1024
                },
                {
                    "type" : "Root",
                    "file system" : "BTRFS"
                }
            ]
        }

    Notes

        The disk layout is set to GPT.

        The EFI System Partition (ESP) and the BIOS Boot partition are created
        with the VFAT file system.

        Partition size should be specified in binary megabytes. Absence of this
        field means that this partition should span the entire remaining disk
        space (minus several sectors for the secondary GPT header and table).

        Root file system can be ether Ext4 or BTRFS.

    """
    stop_if_not_root()
    confirm_disk_destructive_operations()

    device = configuration['device']['path']
    print 'Trying to partition the disk "%s".' % device

    sh('type parted', 'Checking if GNU parted is installed.')
    sh("parted --script '%s' mklabel gpt" % device,
       'Creating the GPT partition scheme on "%s".' % device)

    short_name = configuration['short name']
    partitions = configuration['partitions']
    device_position = 0

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

        sh('parted --script --align optimal ' \
           "'%s' \"mkpart '%s' '%s' '%s' '%s'\"" %
                (device, partition_name, partition_file_system, start, end),
           'Creating partition #%d of type "%s" with name "%s".' %
                (partition_number, partition_type, partition_name))

        if partition_size:
            device_position += partition_size

        if partition_flag:
            sh("parted --script '%s' set %d '%s' on" %
                    (device, partition_number, partition_flag),
               'Setting flag "%s" on partition #%d.' %
                    (partition_flag, partition_number))

        partition_device = device + str(partition_number)
        if partition_file_system == 'vfat':
            sh('type mkfs.vfat', 'Checking if "mkdosfs" is installed.')
            sh("mkfs.vfat -F 32 '%s'" % partition_device,
               'Creating VFAT file system on device "%s".' % partition_device)
        elif partition_file_system == 'linux-swap':
            sh('type mkswap', 'Checking if "util-linux" package is ' \
               'installed and mkswap is present.')
            sh("mkswap '%s'" % partition_device,
               'Setting up the Linux swap partition on device "%s".' %
                    partition_device)
        elif partition_file_system == 'ext4':
            sh('type mkfs.ext4', 'Checking if "e2fsprogs" package is ' \
               ' installed and "mkfs.ext4" is present.')
            sh("mkfs.ext4 '%s'" % partition_device,
               'Creating Ext4 file system on device "%s".' % partition_device)
        elif partition_file_system == 'btrfs':
            sh('type mkfs.btrfs', 'Checking if "btrfs-tools" package is ' \
               'installed and "mkfs.btrfs" is present.')
            sh("mkfs.btrfs '%s'" % partition_device,
               'Creating BTRFS file system on device "%s".' % partition_device)

        if partition_type == 'Root':
            partition_mount_point = '/mnt/%s' % short_name
            sh("mkdir --parents --verbose '%s'" % partition_mount_point,
               'Creating a directory for the root file system mount point at ' \
               '"%s".' % partition_mount_point)
            sh("mount --types '%s' '%s' '%s'" %
                (partition_file_system, partition_device, partition_mount_point)),

        # http://developer.apple.com/library/mac/#technotes/tn2166/_index.html
        if partition_type != 'ESP':
            device_position += 128 # Add space after each partition (excluding
                                   # ESP) for system software to manipulate the
                                   # partition map.

