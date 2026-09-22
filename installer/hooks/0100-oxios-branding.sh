#!/bin/bash
# Install Oxi OS branding: os-release, icons (GNOME Settings -> About),
# Plymouth responsive theme, GRUB theme.
set -e

BRAND_DIR="$(dirname "$0")/../branding"
CHROOT="${CHROOT:-/}"

install -Dm644 "$BRAND_DIR/os-release/os-release" "$CHROOT/etc/os-release"
install -Dm644 "$BRAND_DIR/os-release/os-release" "$CHROOT/usr/lib/os-release"
install -Dm644 "$BRAND_DIR/os-release/lsb-release" "$CHROOT/etc/lsb-release"

for size in 16 32 48 64 128 256 512; do
  install -Dm644 "$BRAND_DIR/icons/oxios-${size}.png" \
    "$CHROOT/usr/share/icons/hicolor/${size}x${size}/apps/oxios.png"
done
install -Dm644 "$BRAND_DIR/icons/oxios-1024.png" \
  "$CHROOT/usr/share/icons/hicolor/scalable/apps/oxios.png"
install -Dm644 "$BRAND_DIR/icons/oxios-256.png" \
  "$CHROOT/usr/share/pixmaps/oxios.png"

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f "$CHROOT/usr/share/icons/hicolor" 2>/dev/null || true
fi

# Plymouth responsive theme (logo top, spinner + bar below).
THEME_DIR="$CHROOT/usr/share/plymouth/themes/oxios"
mkdir -p "$THEME_DIR"
cp -f "$BRAND_DIR"/plymouth/oxios/* "$THEME_DIR/"
if [ "$CHROOT" = "/" ] && command -v plymouth-set-default-theme >/dev/null 2>&1; then
  plymouth-set-default-theme -R oxios 2>/dev/null || \
    plymouth-set-default-theme oxios 2>/dev/null || true
  update-initramfs -u 2>/dev/null || true
fi

# GRUB theme.
GRUB_DIR="$CHROOT/usr/share/grub/themes/oxios"
mkdir -p "$GRUB_DIR"
cp -f "$BRAND_DIR"/grub/oxios/* "$GRUB_DIR/"
mkdir -p "$CHROOT/etc/default/grub.d"
cat > "$CHROOT/etc/default/grub.d/99-oxios.cfg" <<'EOF'
GRUB_THEME="/usr/share/grub/themes/oxios/theme.txt"
GRUB_TIMEOUT=5
GRUB_TIMEOUT_STYLE=menu
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_GFXMODE=auto
GRUB_GFXPAYLOAD_LINUX=keep
EOF

echo "Oxi OS branding installed."
