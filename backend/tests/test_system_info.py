import os
import sys
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault('FLASK_SECRET_KEY', 'appam-system-info-test-secret')
os.environ.setdefault('APPAM_DISABLE_EMBEDDED_WORKER', 'true')
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from app.services.system_info import summarize_storage  # noqa: E402


Partition = namedtuple('Partition', 'device mountpoint fstype opts')
Usage = namedtuple('Usage', 'total used free percent')

GB = 1024 ** 3


def volume(device, mountpoint, total, used, free, fstype='apfs', opts='rw'):
    return Partition(device, mountpoint, fstype, opts), Usage(total, used, free, 0.0)


class StoragePoolTests(unittest.TestCase):
    def test_apfs_volumes_report_their_container_once(self):
        # Every volume of disk3 reports the container's capacity and free space.
        disks = summarize_storage([
            volume('/dev/disk3s1s1', '/', 2000 * GB, 12 * GB, 780 * GB, opts='ro,local,rootfs'),
            volume('/dev/disk3s5', '/System/Volumes/Data', 2000 * GB, 1100 * GB, 780 * GB),
            volume('/dev/disk3s6', '/System/Volumes/VM', 2000 * GB, 4 * GB, 780 * GB),
            volume('/dev/disk3s2', '/System/Volumes/Preboot', 2000 * GB, 8 * GB, 780 * GB),
        ])

        self.assertEqual(len(disks), 1)
        [disk] = disks
        self.assertEqual(disk['mountpoint'], '/')
        self.assertEqual(disk['total'], 2000 * GB)
        self.assertEqual(disk['free'], 780 * GB)
        self.assertEqual(disk['used'], 1220 * GB)
        self.assertAlmostEqual(disk['usage_percent'], 61.0)
        self.assertEqual(len(disk['mountpoints']), 4)

    def test_bind_mounts_of_one_filesystem_are_counted_once(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / 'data'
            data_dir.mkdir()
            hosts = Path(tmpdir) / 'h'
            hosts.write_text('127.0.0.1 localhost\n')
            disks = summarize_storage([
                volume('/dev/vda1', str(hosts), 100 * GB, 40 * GB, 55 * GB, fstype='ext4'),
                volume('/dev/vda1', str(data_dir), 100 * GB, 40 * GB, 55 * GB, fstype='ext4'),
            ])

        self.assertEqual(len(disks), 1)
        # A directory names the disk better than a bind-mounted file does.
        self.assertEqual(disks[0]['mountpoint'], str(data_dir))
        self.assertEqual(disks[0]['total'], 100 * GB)

    def test_separate_disks_stay_separate_and_root_comes_first(self):
        disks = summarize_storage([
            volume('/dev/sdb1', '/mnt/scratch', 4000 * GB, 1000 * GB, 3000 * GB, fstype='xfs'),
            volume('/dev/sda2', '/', 500 * GB, 200 * GB, 275 * GB, fstype='ext4'),
        ])

        self.assertEqual([disk['mountpoint'] for disk in disks], ['/', '/mnt/scratch'])
        # psutil leaves reserved blocks out of both used and free.
        self.assertAlmostEqual(disks[0]['usage_percent'], 200 / 475 * 100)

    def test_read_only_images_and_support_volumes_are_hidden(self):
        disks = summarize_storage([
            volume('/dev/disk3s1s1', '/', 2000 * GB, 12 * GB, 780 * GB, opts='ro,local,rootfs'),
            volume('/dev/disk3s5', '/System/Volumes/Data', 2000 * GB, 1100 * GB, 780 * GB),
            volume('/dev/disk1s2', '/System/Volumes/xarts', 524 * 1024 ** 2, 6 * 1024 ** 2, 500 * 1024 ** 2),
            volume('/dev/disk1s1', '/System/Volumes/iSCPreboot', 524 * 1024 ** 2, 8 * 1024 ** 2, 500 * 1024 ** 2),
            volume('/dev/disk5s1', '/Volumes/Installer', 2 * GB, 2 * GB, 0, fstype='hfs', opts='ro,nodev'),
            volume('/dev/disk6s1', '/Volumes/Archive', 4000 * GB, 1500 * GB, 2500 * GB, fstype='exfat'),
            volume('tmpfs', '/run/empty', 0, 0, 0, fstype='tmpfs'),
        ])

        self.assertEqual([disk['mountpoint'] for disk in disks], ['/', '/Volumes/Archive'])


if __name__ == '__main__':
    unittest.main()
