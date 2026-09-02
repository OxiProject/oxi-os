# OxiOS Build Guide

## Base
Debian 13 (Trixie) Stable

## Build Tools
- live-build
- debootstrap

## Build Command
lb config \
  --distribution trixie \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --archive-areas "main contrib non-free non-free-firmware" \
  --debian-installer false \
  --backports true \
  --security true \
  --updates true

## Build Steps
1. `lb config` - Configure live-build
2. `sudo lb build` - Build the ISO

## Features
- **Minimal XFS-only system**: Only XFS filesystem support for performance
- **Latest kernel**: Automatically installs kernel from Debian backports
- **NVIDIA auto-detection**: Calamares module detects NVIDIA hardware and installs proprietary drivers during installation
- **Custom branding**: OxiOS logo on Calamares installer, GRUB bootloader, and Plymouth boot animation
- **Pre-installed applications**: LibreOffice, GNOME desktop, Flatpak support
- **Gaming ready**: PipeWire, WirePlumber, and firmware for gaming

## Partitioning
- Default filesystem: XFS
- EFI System Partition: /boot/efi
- LUKS encryption support: Enabled
- Swap: Optional (user choice)

## Calamares Modules Added
- `backports-kernel`: Installs latest kernel from Debian backports
- `nvidia-driver`: Auto-detects NVIDIA GPU and installs proprietary drivers
- Custom branding: oxios

## Boot Configuration
- Plymouth theme: oxios (custom boot animation with logo)
- GRUB theme: oxios (custom bootloader theme with logo)
- Boot parameters: quiet splash

## Post-Install
- APT sources configured with backports repository
- NVIDIA drivers installed if hardware detected
- GRUB updated with custom theme
- Initramfs updated with Plymouth theme
