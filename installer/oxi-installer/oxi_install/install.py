"""System install orchestration: debootstrap Sid, branding, boot setup."""
from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from .partitioning import Plan, format_commands, mount_commands, sgdisk_commands

Progress = Callable[[float, str], None]

SUITE = "sid"
MIRROR = "https://deb.debian.org/debian"
AREAS = "main contrib non-free non-free-firmware"
TARGET_SERVICES = ("gdm", "NetworkManager")


def notify(progress: Progress | None, fraction: float, message: str) -> None:
    if progress:
        progress(max(0.0, min(1.0, fraction)), message)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def prepare_disk(plan: Plan, target: str, progress: Progress | None = None) -> None:
    from . import partitioning

    notify(progress, 0.02, f"Partitioning {plan.disk} (XFS root)…")
    for cmd in sgdisk_commands(plan):
        run(cmd)
    run(["partprobe", plan.disk])
    notify(progress, 0.10, "Formatting EFI + XFS root…")
    for cmd in format_commands(plan):
        run(cmd)
    notify(progress, 0.16, "Mounting target system…")
    os.makedirs(target, exist_ok=True)
    for cmd in mount_commands(plan, target):
        run(cmd)
    with open(f"{target}/etc/fstab", "w", encoding="utf-8") as fh:
        fh.write("# Oxi OS fstab — XFS root\n")
        for entry in partitioning.fstab_entries(plan):
            fh.write(entry + "\n")


def bootstrap(target: str, progress: Progress | None = None) -> None:
    notify(progress, 0.22, "Bootstrapping Debian Sid base…")
    run(["debootstrap", f"--components={AREAS}", SUITE, target, MIRROR])
    notify(progress, 0.45, "Configuring APT for Sid…")
    sources = target + "/etc/apt/sources.list.d/oxios.sources"
    os.makedirs(os.path.dirname(sources), exist_ok=True)
    Path(sources).write_text(
        "Types: deb\nURIs: https://deb.debian.org/debian\n"
        "Suites: sid\nComponents: main contrib non-free non-free-firmware\n"
        "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg\n",
        encoding="utf-8",
    )
    run(["chroot", target, "apt-get", "update"])


def install_packages(target: str, packages: list[str],
                     progress: Progress | None = None) -> None:
    notify(progress, 0.52, f"Installing {len(packages)} packages…")
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    subprocess.run(
        ["chroot", target, "apt-get", "install", "-y", *packages],
        check=True, env=env)
    notify(progress, 0.80, "Packages installed.")


def apply_branding(target: str, branding_dir: str) -> None:
    """Copy os-release, icons, Plymouth and GRUB assets into the target."""
    brand = Path(branding_dir)
    shutil.copy2(brand / "os-release" / "os-release", f"{target}/etc/os-release")
    os.makedirs(f"{target}/usr/lib", exist_ok=True)
    shutil.copy2(brand / "os-release" / "os-release", f"{target}/usr/lib/os-release")
    shutil.copy2(brand / "os-release" / "lsb-release", f"{target}/etc/lsb-release")

    icons = brand / "icons"
    for size in (16, 32, 48, 64, 128, 256, 512):
        dest = Path(f"{target}/usr/share/icons/hicolor/{size}x{size}/apps")
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icons / f"oxios-{size}.png", dest / "oxios.png")
    scalable = Path(f"{target}/usr/share/icons/hicolor/scalable/apps")
    scalable.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icons / "oxios-1024.png", scalable / "oxios.png")
    pixmaps = Path(f"{target}/usr/share/pixmaps")
    pixmaps.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icons / "oxios-256.png", pixmaps / "oxios.png")
    subprocess.run(
        ["chroot", target, "gtk-update-icon-cache", "-f",
         "/usr/share/icons/hicolor"], check=False)

    theme = Path(f"{target}/usr/share/plymouth/themes/oxios")
    theme.mkdir(parents=True, exist_ok=True)
    for asset in (brand / "plymouth" / "oxios").iterdir():
        shutil.copy2(asset, theme / asset.name)
    subprocess.run(
        ["chroot", target, "plymouth-set-default-theme", "-R", "oxios"],
        check=False)
    subprocess.run(["chroot", target, "update-initramfs", "-u"], check=False)


def configure_boot(target: str, plan: Plan) -> None:
    grub_dir = Path(f"{target}/usr/share/grub/themes/oxios")
    grub_dir.mkdir(parents=True, exist_ok=True)
    for asset in ("background.png", "unicode.pf2"):
        src = Path(__file__).resolve().parent.parent.parent / "branding" / "grub" / "oxios" / asset
        if src.exists():
            shutil.copy2(src, grub_dir / asset)
    grub_dir.joinpath("theme.txt").write_text(GRUB_THEME, encoding="utf-8")
    grub_d = Path(f"{target}/etc/default/grub.d")
    grub_d.mkdir(parents=True, exist_ok=True)
    grub_d.joinpath("99-oxios.cfg").write_text(
        'GRUB_THEME="/usr/share/grub/themes/oxios/theme.txt"\n'
        "GRUB_TIMEOUT=5\nGRUB_TIMEOUT_STYLE=menu\n"
        'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n'
        "GRUB_GFXMODE=auto\nGRUB_GFXPAYLOAD_LINUX=keep\n",
        encoding="utf-8",
    )
    efi_id = "OxiOS"
    subprocess.run(
        ["chroot", target, "grub-install", "--target=x86_64-efi",
         "--efi-directory=/boot/efi", f"--bootloader-id={efi_id}",
         "--recheck"],
        check=False,
    )
    subprocess.run(
        ["chroot", target, "grub-install", "--target=i386-pc", plan.disk],
        check=False,
    )
    subprocess.run(["chroot", target, "update-grub"], check=False)


def finish(target: str, username: str, password: str, fullname: str,
           timezone: str, progress: Progress | None = None) -> None:
    from . import usersetup

    notify(progress, 0.86, "Creating user…")
    usersetup.create_user(target, username, password, fullname)
    usersetup.lock_root(target)
    usersetup.set_locale(target)
    usersetup.set_timezone(target, timezone)
    notify(progress, 0.93, "Enabling desktop services…")
    usersetup.enable_services(target, TARGET_SERVICES)
    for svc in TARGET_SERVICES:
        subprocess.run(["chroot", target, "systemctl", "enable", svc], check=False)


GRUB_THEME = """# Oxi OS GRUB theme — responsive (percent-based layout).
title-text: "Oxi OS"
title-font: "DejaVu Sans Bold 16"
title-color: "#ffffff"

desktop-image: "background.png"
desktop-color: "#000000"
terminal-font: "unicode"

+ boot_menu {
    left = 20%
    top = 30%
    width = 60%
    height = 45%
    item_font = "DejaVu Sans 14"
    item_color = "#ffffff"
    selected_item_color = "#18a999"
    selected_item_pixmap_style = "select_*.png"
    item_height = 32
    item_padding = 12
    item_spacing = 8
    icon_width = 32
    icon_height = 32
    item_icon_space = 12
    scrollbar = true
}

+ label {
    top = 82%
    left = 50%
    width = 10%
    align = "center"
    text = "Oxi OS"
    color = "#ffffff"
    font = "DejaVu Sans 12"
}

+ progress_bar {
    id = "__timeout__"
    left = 20%
    width = 60%
    top = 88%
    height = 12
    fg_color = "#18a999"
    bg_color = "#2a2a2a"
    border_color = "#000000"
    text = "@TIMEOUT_NOTIFICATION_LONG@"
    font = "DejaVu Sans 10"
    text_color = "#888888"
}
"""
