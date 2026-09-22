"""Disk partitioning for the Oxi OS installer — XFS-only root on UEFI."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


ROOT_FS = "xfs"
EFI_SIZE_MIB = 512
EFI_MOUNT = "/boot/efi"

# Device prefixes that are never install targets.
_VIRTUAL_PREFIXES = ("loop", "ram", "sr", "fd", "zd", "dm-", "zram")


@dataclass
class Plan:
    disk: str
    efi_size_mib: int = EFI_SIZE_MIB
    encrypt: bool = False

    @property
    def root_mount(self) -> str:
        return "/"

    @property
    def root_fs(self) -> str:
        return ROOT_FS


def _is_virtual(name: str) -> bool:
    return name.startswith(_VIRTUAL_PREFIXES)


def part_path(disk: str, number: int) -> str:
    """Partition device path for *disk* (handles NVMe/mmcblk 'pN' suffix)."""
    if disk.startswith("/dev/nvme") or disk.startswith("/dev/mmcblk"):
        return f"{disk}p{number}"
    return f"{disk}{number}"


def list_disks() -> list[dict]:
    """Return candidate target disks as {path, size, model} dicts.

    Uses ``lsblk --json`` so MODEL strings containing spaces can never
    shift the TYPE column (the old text-column parser dropped every
    real disk whose vendor string contained a space).
    """
    try:
        out = subprocess.run(
            ["lsblk", "-d", "-n", "-b", "-J", "-o", "NAME,PATH,SIZE,MODEL,TYPE"],
            capture_output=True, text=True, check=True,
        )
        devices = json.loads(out.stdout).get("blockdevices", [])
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        return []
    disks = []
    for dev in devices:
        name = dev.get("name", "")
        if dev.get("type") != "disk" or _is_virtual(name):
            continue
        size = int(dev.get("size") or 0)
        model = (dev.get("model") or "").strip() or name
        disks.append({
            "path": dev.get("path") or f"/dev/{name}",
            "size": size,
            "size_gb": round(size / 1e9),
            "model": model,
            "label": f"{model} — {round(size / 1e9)} GB",
        })
    return disks


def sgdisk_commands(plan: Plan) -> list[list[str]]:
    """sgdisk invocations that lay down GPT + EFI + XFS root."""
    return [
        ["sgdisk", "--zap-all", plan.disk],
        ["sgdisk", "--new=1:0:+%dMiB" % plan.efi_size_mib,
         "--typecode=1:EF00", "--change-name=1:EFI System Partition", plan.disk],
        ["sgdisk", "--new=2:0:0", "--typecode=2:8300",
         "--change-name=2:OxiOS root", plan.disk],
    ]


def format_commands(plan: Plan) -> list[list[str]]:
    """Format EFI as FAT32 and root as XFS (encrypted root optional)."""
    efi_part, root_part = part_path(plan.disk, 1), part_path(plan.disk, 2)
    cmds = [["mkfs.vfat", "-F32", "-n", "EFI", efi_part]]
    if plan.encrypt:
        cmds.append(["cryptsetup", "luksFormat", "--batch-mode", root_part])
        cmds.append(["cryptsetup", "open", root_part, "oxi_root"])
        cmds.append(["mkfs.xfs", "-f", "-L", "oxios", "/dev/mapper/oxi_root"])
    else:
        cmds.append(["mkfs.xfs", "-f", "-L", "oxios", root_part])
    return cmds


def mount_commands(plan: Plan, target: str) -> list[list[str]]:
    """Mount the new system at *target*."""
    root_part = "/dev/mapper/oxi_root" if plan.encrypt else part_path(plan.disk, 2)
    return [
        ["mount", "-t", ROOT_FS, root_part, target],
        ["mkdir", "-p", f"{target}{EFI_MOUNT}"],
        ["mount", part_path(plan.disk, 1), f"{target}{EFI_MOUNT}"],
    ]


def fstab_entries(plan: Plan) -> list[str]:
    """fstab lines for the installed system (XFS root)."""
    root_part = "/dev/mapper/oxi_root" if plan.encrypt else part_path(plan.disk, 2)
    entries = [f"{root_part}  /  {ROOT_FS}  defaults  0  1"]
    entries.append(f"{part_path(plan.disk, 1)}  {EFI_MOUNT}  vfat  umask=0077,shortname=winnt  0  1")
    return entries
