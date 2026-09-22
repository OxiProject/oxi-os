#!/bin/bash
# Make XFS the only advertised root filesystem for the installer.
set -e

command -v mkfs.xfs >/dev/null 2>&1 || {
  echo "xfsprogs is required (mkfs.xfs not found)" >&2
  exit 1
}

mkdir -p /etc/oxi-installer
cat > /etc/oxi-installer/filesystems.conf <<'EOF'
# Oxi OS installer: XFS-only root.
ROOT_FS=xfs
ALLOWED_ROOT_FS=xfs
EFI_FS=vfat
EOF

echo "XFS-only root enforced."
