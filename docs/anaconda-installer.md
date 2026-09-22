# Oxi OS Anaconda-Style Installer

This document describes the custom Anaconda-style installer for Oxi OS, a Debian Sid-based distribution with XFS root filesystem, responsive Plymouth boot animation, and GNOME Settings integration.

## Architecture Overview

```
installer/
├── branding/           # Visual assets (Plymouth, GRUB, icons, os-release)
├── hooks/              # live-build chroot hooks (branding, XFS enforcement)
├── kickstart/          # Anaconda kickstart file (oxios-xfs.ks)
├── oxi-installer/      # Python/GTK4 GUI installer (oxi_install package)
├── product/            # Product definition & package manifest
└── scripts/            # ISO build script (build-iso.sh)
```

## Key Features

### 1. XFS-Only Root Filesystem
- **Partitioning**: GPT + 512 MiB FAT32 EFI + XFS root (grows to fill disk)
- **No ext4 option**: Enforced by `hooks/0200-oxios-xfs-only.sh` and kickstart
- **fstab**: XFS root with `defaults`, EFI with `umask=0077,shortname=winnt`

### 2. Responsive Plymouth Boot Theme (`branding/plymouth/oxios/`)
- **Logo**: Scales to 30% of smallest screen dimension, centered at 36% height
- **Spinner**: 12 dots in a circle below logo, radius 5.5% of screen
- **Progress bar**: 36% screen width (clamped 200–480px), at 86% height
- **Multi-monitor safe**: Uses `Window.GetX()*2 + Window.GetWidth()` pattern
- **Callbacks**: `SetRefreshFunction`, `SetBootProgressFunction`, `SetQuitFunction`, `SetMessageFunction`, `SetDisplayNormalFunction`

### 3. Responsive GRUB Theme (`branding/grub/oxios/`)
- **Percent-based layout**: Menu at 20%/30%/60%/45%, progress bar at 88%
- **Single font**: `unicode.pf2` (DejaVu Sans Regular 16) — only font shipped
- **Background**: 1920×1080 PNG with centered logo, scales via `desktop-image`

### 4. GNOME Settings → About Integration
- **os-release**: `LOGO=oxios` + `ID=oxios`
- **Icons**: hicolor theme at 16/32/48/64/128/256/512 + scalable (1024)
- **pixmaps**: `/usr/share/pixmaps/oxios.png` (256px fallback)

### 5. Python/GTK4 Installer GUI (`oxi-installer/oxi_install/`)
- **Hub page**: Disk selector (ComboRow), encryption toggle, fixed XFS label, timezone
- **User page**: Full name, username (validated), password (confirmed)
- **Progress page**: Real-time log, progress bar, reboot button
- **Backend**: debootstrap Sid → APT → packages → branding → GRUB/Plymouth → user setup

## Building the ISO

```bash
# Requires: live-build, debootstrap, grub-mkfont, ffmpeg, xfsprogs, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1
sudo ./installer/scripts/build-iso.sh [--output DIR] [--suite sid] [--arch amd64]
```

Output: `oxios-sid-amd64.iso` (hybrid ISO, boots UEFI + BIOS)

## Testing

```bash
# Unit tests (no root, no disks touched)
cd installer && python3 -m unittest discover -s tests -v

# Syntax checks
bash -n scripts/build-iso.sh hooks/*.sh kickstart/oxios-xfs.ks
python3 -m py_compile oxi-installer/oxi_install/*.py

# Disk listing on real hardware
cd oxi-installer && python3 -c "from oxi_install.partitioning import list_disks; print(list_disks())"
```

## Configuration Files

| File | Purpose |
|------|---------|
| `kickstart/oxios-xfs.ks` | Anaconda kickstart (XFS layout, packages, %post branding) |
| `product/oxios-packages.manifest` | Sectioned package list for live-build |
| `branding/os-release/os-release` | `LOGO=oxios`, `ID=oxios`, `PRETTY_NAME="Oxi OS"` |
| `hooks/0100-oxios-branding.sh` | Chroot hook: copies branding, enables Plymouth/GRUB |
| `hooks/0200-oxios-xfs-only.sh` | Chroot hook: enforces XFS-only, creates `/etc/oxi-installer/filesystems.conf` |

## Plymouth Script API Notes (Validated Against Debian Themes)

- `Math.Pi` is a **constant**, not a function — use `Math.Pi` not `Math.Pi()`
- `for (i = 0; i < N; i++)` — array indexing `N[i]` in condition is invalid
- Hex literals (`0x...`) **not supported** — use decimal
- `%` operator **supported** (maps to `fmodl`)
- `Image.Scale(width, height)` and `Image.Crop(x, y, w, h)` **available**
- `Window.GetWidth()` / `Window.GetHeight()` — no args or `(0)` both work
- `Plymouth.GetMode()` returns `"boot"` / `"shutdown"` / etc.
- `Sprite.SetImage()`, `.SetPosition(x, y, z)`, `.SetOpacity(0..1)` — standard
- `global.var = value` for persistent state across callbacks

## GRUB Theme Font Notes

- `grub-mkfont --ascii-bitmaps` **not available** in current Debian — only `-o unicode.pf2`
- Theme must reference only `"unicode"` font family
- `selected_item_pixmap_style = "select_*.png"` removed (assets not shipped)

## Kickstart Notes

- `user --name=oxi --groups=sudo --lock --plaintext` — no default password baked in
- Real user created by GUI installer during installation
- `%post` section wires branding from `/run/install/repo/oxios/` (ISO payload path)

## Package Sync

Keep these three in sync:
1. `installer/kickstart/oxios-xfs.ks` (%packages section)
2. `installer/product/oxios-packages.manifest` (sectioned manifest)
3. `installer/oxi-installer/oxi_install/gui.py` (`DEFAULT_PACKAGES` list)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Disk list empty in GUI | `lsblk` text parser broke on model with spaces | Fixed: use `lsblk --json` |
| NVMe partition path wrong | Used `/dev/nvme0n12` instead of `/dev/nvme0n1p2` | Fixed: `part_path()` helper |
| Plymouth theme not loading | `plymouth-set-default-theme -R` fails in chroot | Fallback to non-`-R` then `update-initramfs -u` |
| GRUB font missing | Theme references `DejaVu Sans` but only `unicode.pf2` shipped | Fixed: all widgets use `unicode` |
| About logo not showing | `LOGO=oxios` but no hicolor icons installed | Fixed: hook installs full icon set + `gtk-update-icon-cache` |

## References

- Plymouth script API: `/usr/share/plymouth/themes/{spacefun,softwaves,lines,moonlight}/*.script`
- GRUB theme format: `info grub` → "Theme File Format"
- live-build: `man lb_config`, `man lb_build`
- Anaconda kickstart: `man kickstart` (RHEL/Fedora docs apply)

## Calamares Config Schema Notes (3.3.x)

The live ISO also ships Calamares configs under
`live-build/config/includes.chroot/etc/calamares/`. These were validated
against the installed Calamares 3.3.14 module code (`main.py` + `strings`
on the `.so` files), not just upstream docs:

- `unpackfs.conf` uses an `unpack:` list (`source`/`sourcefs`/`destination`);
  the old `targetRoot`/`copyMethod` keys are ignored by `unpackfs/main.py`.
- `bootloader.conf` uses upstream key names (`grubInstall`, `grubMkconfig`,
  `efiBootloaderId`, ...); GRUB theme/cmdline lives in `grubcfg.conf`
  (`prefer_grub_d: true`), sequenced before `bootloader` in `settings.conf`.
- `services-systemd.conf` uses a `units:` list (`name`/`action`/`mandatory`);
  the old `enabledServices`/`disabledServices` keys are ignored.
- `users.conf` sets `setRootPassword: false` (no default root password;
  the GUI-created user gets sudo).
