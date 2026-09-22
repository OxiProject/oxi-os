# OxiOS Build Guide

## Base
Debian Sid (Unstable)

## Build Tools
- live-build
- debootstrap

## Build Command
lb config \
  --distribution sid \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --archive-areas "main contrib non-free non-free-firmware" \
  --debian-installer false \
  --security true

## Build Steps
1. `lb config` - Configure live-build
2. `sudo lb build` - Build the ISO

## Features
- **Debian Sid rolling release**: Always latest packages
- **Minimal XFS-only system**: Only XFS filesystem support for performance
- **Latest kernel**: Debian Sid ships the newest kernel; no extra module needed
- **NVIDIA auto-detection**: Calamares module detects NVIDIA hardware and installs proprietary drivers during installation
- **Custom branding**: OxiOS logo on Calamares installer, GRUB bootloader, and Plymouth boot animation
- **Pre-installed applications**: LibreOffice, GNOME desktop, Flatpak support
- **Gaming ready**: PipeWire, WirePlumber, and firmware for gaming

## Partitioning
- Default filesystem: XFS
- EFI System Partition: /boot/efi
- LUKS encryption support: Enabled
- Swap: Optional (user choice)

## Calamares Modules
- `partition` (XFS-only), `unpackfs` (`unpack:` list format), `bootloader`
  (upstream key names), `grubcfg` (GRUB defaults via `/etc/default/grub.d/`),
  `services-systemd` (`units:` list format), `users` (no root password),
  `displaymanager` (GDM), `welcome`, `locale`, `keyboard`, `networkcfg`,
  `localecfg`, `hwclock`, `fstab`, `mount`, `machineid`
- Custom branding: oxios (see `installer/branding/`)
- `latest-kernel` module was removed: Debian Sid already carries the newest
  kernel, so no post-install kernel swap is needed

## Boot Configuration
- Plymouth theme: oxios (custom boot animation with logo)
- GRUB theme: oxios (custom bootloader theme with logo)
- Boot parameters: quiet splash

## Post-Install
- APT sources configured for Debian Sid
- NVIDIA drivers installed if hardware detected
- GRUB updated with custom theme
- Initramfs updated with Plymouth theme

## Anaconda-Style Installer Build

The installer is built as part of the live ISO via `installer/scripts/build-iso.sh`.

### Prerequisites

```bash
sudo apt update && sudo apt install -y \
  live-build debootstrap grub-mkfont ffmpeg xfsprogs \
  python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
  python3-parted python3-yaml
```

### Build Process

1. `lb config` — Debian Sid, amd64, iso-hybrid, main/contrib/non-free/non-free-firmware
2. Package list from `installer/product/oxios-packages.manifest` → `config/package-lists/oxios.list.chroot`
3. Installer payload → `config/includes.chroot/usr/share/oxi-installer/`
4. Branding payload → `config/includes.chroot/usr/share/oxios/branding/`
5. Desktop entry → `config/includes.chroot/usr/share/applications/install-oxios.desktop`
6. Branding hook → `config/hooks/normal/0100-oxios-branding.hook.chroot`
7. `lb build` — produces `live-image-*.hybrid.iso`
8. Rename to `oxios-sid-amd64.iso`

### Payload Contents

| Source | Destination in ISO |
|--------|-------------------|
| `installer/oxi-installer/` | `/usr/share/oxi-installer/` |
| `installer/kickstart/` | `/usr/share/oxi-installer/kickstart/` |
| `installer/product/` | `/usr/share/oxi-installer/product/` |
| `installer/branding/` | `/usr/share/oxios/branding/` |

### Testing the ISO

```bash
# Quick boot test (QEMU)
qemu-system-x86_64 -enable-kvm -m 4G -cdrom oxios-sid-amd64.iso

# Verify XFS root in installed system
lsblk -f | grep xfs

# Verify Plymouth theme
plymouth-set-default-theme --list | grep oxios

# Verify GRUB theme
grep GRUB_THEME /etc/default/grub.d/99-oxios.cfg

# Verify About logo
grep LOGO /etc/os-release
ls /usr/share/icons/hicolor/*/apps/oxios.png
```
