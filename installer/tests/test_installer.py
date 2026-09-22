"""Smoke tests for the Oxi OS installer (no root, no disks touched)."""
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "oxi-installer"))

from oxi_install import partitioning  # noqa: E402
from oxi_install import usersetup  # noqa: E402


class PartitioningTest(unittest.TestCase):
    def test_root_is_xfs_only(self):
        plan = partitioning.Plan(disk="/dev/sda")
        self.assertEqual(plan.root_fs, "xfs")

    def test_sgdisk_lays_gpt_efi_xfs(self):
        cmds = partitioning.sgdisk_commands(partitioning.Plan(disk="/dev/sda"))
        flat = " ".join(" ".join(c) for c in cmds)
        self.assertIn("EF00", flat)
        self.assertIn("8300", flat)

    def test_format_uses_mkfs_xfs_and_vfat_efi(self):
        cmds = partitioning.format_commands(partitioning.Plan(disk="/dev/sda"))
        flat = " ".join(" ".join(c) for c in cmds)
        self.assertIn("mkfs.xfs", flat)
        self.assertIn("mkfs.vfat", flat)

    def test_fstab_mounts_xfs_root(self):
        entries = partitioning.fstab_entries(partitioning.Plan(disk="/dev/sda"))
        root = [e for e in entries if e.split()[1] == "/"][0]
        self.assertIn("xfs", root)

    def test_list_disks_skips_virtual(self):
        self.assertIsInstance(partitioning.list_disks(), list)

    def test_part_path_handles_nvme_and_mmcblk(self):
        plan = partitioning.Plan(disk="/dev/nvme0n1")
        self.assertEqual(partitioning.part_path(plan.disk, 1), "/dev/nvme0n1p1")
        plan = partitioning.Plan(disk="/dev/mmcblk0")
        self.assertEqual(partitioning.part_path(plan.disk, 2), "/dev/mmcblk0p2")
        plan = partitioning.Plan(disk="/dev/sda")
        self.assertEqual(partitioning.part_path(plan.disk, 1), "/dev/sda1")

    def test_list_disks_parses_json_with_spaced_model(self):
        import json
        from unittest import mock
        fake = {"blockdevices": [
            {"name": "sda", "size": 512110190592, "model": "Samsung SSD 860",
             "type": "disk", "rm": False, "ro": False},
            {"name": "loop0", "size": 123, "model": None,
             "type": "loop", "rm": False, "ro": True},
        ]}
        completed = subprocess.CompletedProcess(
            args=["lsblk"], returncode=0, stdout=json.dumps(fake))
        with mock.patch.object(subprocess, "run", return_value=completed):
            disks = partitioning.list_disks()
        self.assertEqual(len(disks), 1)
        self.assertEqual(disks[0]["path"], "/dev/sda")
        self.assertIn("Samsung", disks[0]["label"])


class UserSetupTest(unittest.TestCase):
    def test_username_rules(self):
        self.assertTrue(usersetup.valid_username("oxi"))
        self.assertFalse(usersetup.valid_username("Oxi User!"))
        self.assertFalse(usersetup.valid_username(""))


class BrandingAssetsTest(unittest.TestCase):
    def test_theme_assets_exist(self):
        base = os.path.join(REPO, "branding")
        for rel in (
            "plymouth/oxios/oxios.script",
            "plymouth/oxios/oxios.plymouth",
            "plymouth/oxios/logo.png",
            "plymouth/oxios/dot.png",
            "plymouth/oxios/track.png",
            "plymouth/oxios/fill.png",
            "grub/oxios/theme.txt",
            "grub/oxios/background.png",
            "grub/oxios/unicode.pf2",
            "os-release/os-release",
            "icons/oxios-256.png",
        ):
            self.assertTrue(os.path.exists(os.path.join(base, rel)), rel)

    def test_os_release_points_about_logo(self):
        path = os.path.join(REPO, "branding", "os-release", "os-release")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("LOGO=oxios", text)
        self.assertIn("Oxi OS", text)

    def test_plymouth_script_is_responsive(self):
        path = os.path.join(REPO, "branding", "plymouth", "oxios", "oxios.script")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Window.GetWidth", text)
        self.assertIn("SetBootProgressFunction", text)
        self.assertIn("SetRefreshFunction", text)

    def test_kickstart_is_xfs_only(self):
        path = os.path.join(REPO, "kickstart", "oxios-xfs.ks")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("--fstype=xfs", text)
        self.assertNotIn("--fstype=ext4", text)


if __name__ == "__main__":
    unittest.main()


class CalamaresConfigTest(unittest.TestCase):
    CAL = os.path.join(REPO, "..", "live-build", "config", "includes.chroot",
                       "etc", "calamares")

    def _read(self, *parts):
        with open(os.path.join(self.CAL, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_unpackfs_uses_unpack_list(self):
        text = self._read("modules", "unpackfs.conf")
        self.assertIn("unpack:", text)
        self.assertIn("sourcefs:", text)
        self.assertNotIn("copyMethod", text)

    def test_bootloader_keys_match_module(self):
        text = self._read("modules", "bootloader.conf")
        for key in ("efiBootLoader", "grubInstall", "grubMkconfig",
                    "efiBootloaderId", "installEFIFallback"):
            self.assertIn(key, text)
        self.assertNotIn("installerModule", text)

    def test_services_uses_units_list(self):
        text = self._read("modules", "services-systemd.conf")
        self.assertIn("units:", text)
        self.assertIn("action:", text)
        self.assertNotIn("enabledServices", text)

    def test_users_has_no_root_password(self):
        text = self._read("modules", "users.conf")
        self.assertIn("setRootPassword: false", text)
        self.assertNotIn("avatar", text)

    def test_grubcfg_in_sequence(self):
        text = self._read("settings.conf")
        self.assertIn("- grubcfg", text)
