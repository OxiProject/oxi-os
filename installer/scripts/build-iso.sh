#!/bin/bash
# Build the Oxi OS live ISO (Debian Sid) with the Anaconda-style installer.
#
# Usage:
#   sudo scripts/build-iso.sh [--output DIR] [--suite sid] [--arch amd64]
#
# The ISO boots a GNOME live session with "Install Oxi OS" on the desktop.
# The installer lays down an XFS root, the responsive Plymouth theme
# (logo top, loading indicator below) and the About-page logo.
set -e

SUITE="sid"
ARCH="amd64"
OUTPUT="$PWD"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --output) OUTPUT="$2"; shift 2 ;;
    --suite) SUITE="$2"; shift 2 ;;
    --arch) ARCH="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

command -v lb >/dev/null 2>&1 || { echo "live-build (lb) is required" >&2; exit 1; }

WORK="$OUTPUT/oxios-iso-build"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

lb config \
  --distribution "$SUITE" \
  --architectures "$ARCH" \
  --binary-images iso-hybrid \
  --archive-areas "main contrib non-free non-free-firmware" \
  --debian-installer false \
  --security true \
  --bootappend-live "boot=live components quiet splash" \
  --iso-application "Oxi OS" \
  --iso-publisher "Oxi OS Project" \
  --iso-volume "OxiOS"

# Desktop + installer payload.
mkdir -p config/package-lists
awk '
  /^#/ || /^$/ { next }
  /^\[/ { section=$0; next }
  { print $1 }
' "$REPO_ROOT/installer/product/oxios-packages.manifest" \
  > config/package-lists/oxios.list.chroot
cat >> config/package-lists/oxios.list.chroot <<'EOF'
live-boot
live-config
live-config-systemd
systemd-sysv
EOF

# Installer code + kickstart + branding payload.
mkdir -p config/includes.chroot/usr/share/oxi-installer \
         config/includes.chroot/usr/share/oxios \
         config/includes.chroot/usr/share/applications
cp -r "$REPO_ROOT/installer/oxi-installer" config/includes.chroot/usr/share/oxi-installer/
cp -r "$REPO_ROOT/installer/kickstart" config/includes.chroot/usr/share/oxi-installer/
cp -r "$REPO_ROOT/installer/product" config/includes.chroot/usr/share/oxi-installer/
cp -r "$REPO_ROOT/installer/branding" config/includes.chroot/usr/share/oxios/branding
chmod +x config/includes.chroot/usr/share/oxi-installer/bin/oxi-installer
ln -sf /usr/share/oxi-installer/bin/oxi-installer \
  config/includes.chroot/usr/bin/oxi-installer

# Desktop entry for the installer.
cat > config/includes.chroot/usr/share/applications/install-oxios.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Install Oxi OS
Comment=Install Oxi OS to disk (XFS root)
Exec=pkexec /usr/bin/oxi-installer
Icon=oxios
Terminal=false
Categories=System;
EOF

# Branding hook.
mkdir -p config/hooks/normal
cat > config/hooks/normal/0100-oxios-branding.hook.chroot <<'EOF'
#!/bin/bash
set -e
BRAND=/usr/share/oxios/branding
install -Dm644 "$BRAND/os-release/os-release" /etc/os-release
install -Dm644 "$BRAND/os-release/os-release" /usr/lib/os-release
install -Dm644 "$BRAND/os-release/lsb-release" /etc/lsb-release
for size in 16 32 48 64 128 256 512; do
  install -Dm644 "$BRAND/icons/oxios-${size}.png" \
    "/usr/share/icons/hicolor/${size}x${size}/apps/oxios.png"
done
install -Dm644 "$BRAND/icons/oxios-1024.png" \
  /usr/share/icons/hicolor/scalable/apps/oxios.png
install -Dm644 "$BRAND/icons/oxios-256.png" /usr/share/pixmaps/oxios.png
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
mkdir -p /usr/share/plymouth/themes/oxios
cp -f "$BRAND"/plymouth/oxios/* /usr/share/plymouth/themes/oxios/
plymouth-set-default-theme -R oxios 2>/dev/null || \
  plymouth-set-default-theme oxios 2>/dev/null || true
update-initramfs -u 2>/dev/null || true
mkdir -p /usr/share/grub/themes/oxios
cp -f "$BRAND"/grub/oxios/* /usr/share/grub/themes/oxios/
mkdir -p /etc/default/grub.d
printf '%s\n' \
  'GRUB_THEME="/usr/share/grub/themes/oxios/theme.txt"' \
  'GRUB_TIMEOUT=5' \
  'GRUB_TIMEOUT_STYLE=menu' \
  'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"' \
  'GRUB_GFXMODE=auto' \
  'GRUB_GFXPAYLOAD_LINUX=keep' \
  > /etc/default/grub.d/99-oxios.cfg
EOF
chmod +x config/hooks/normal/0100-oxios-branding.hook.chroot

lb build

ISO="$(ls -1 live-image-*.hybrid.iso 2>/dev/null | head -n1 || true)"
if [ -n "$ISO" ]; then
  mv "$ISO" "$OUTPUT/oxios-sid-${ARCH}.iso"
  echo "ISO ready: $OUTPUT/oxios-sid-${ARCH}.iso"
else
  echo "Build finished, no ISO found in $WORK" >&2
  exit 1
fi
