# Oxi OS kickstart — Debian Sid, GNOME, XFS-only root.
#
# Layout (UEFI):
#   /boot/efi  FAT32  512 MiB
#   /          XFS    rest of disk
#
# XFS note: the installer formats / as XFS and passes
# "rootfstype=xfs" so kernels without an XFS module can still mount root.

lang en_US.UTF-8
keyboard us
timezone --utc Etc/UTC
network --bootproto=dhcp --device=link --activate

# ---- storage: XFS everywhere, no other root filesystem offered ----
clearpart --all --initlabel --drives=sda
part /boot/efi --fstype=vfat --size=512 --fsoptions="umask=0077,shortname=winnt"
part / --fstype=xfs --grow

bootloader --location=mbr --boot-drive=sda --timeout=5 --append="quiet splash"

rootpw --lock
# NOTE: no default user/password is baked into the image.
# The "Install Oxi OS" GUI creates the real user account during install.
user --name=oxi --groups=sudo --lock --plaintext

%packages --excludedocs
# --- Oxi OS desktop base (Debian Sid, GNOME) ---
gnome
gnome-shell
gnome-session
gnome-control-center
gnome-terminal
nautilus
gdm3
gnome-software
gnome-text-editor
gnome-calculator
gnome-system-monitor
gnome-disk-utility
gnome-tweaks
baobab
file-roller
eog
evince
yelp
pipewire
wireplumber
pipewire-audio
pipewire-pulse
network-manager
flatpak
xfsprogs
plymouth
plymouth-themes
linux-image-amd64
sudo
bash-completion
curl
ca-certificates
os-prober
firmware-linux
firmware-linux-free
firmware-sof-signed
%end

services --enabled=gdm,NetworkManager
xconfig --defaultdesktop=GNOME

%post --erroronfail
# Keep APT on Debian Sid.
cat > /etc/apt/sources.list.d/oxios.sources <<'EOF'
Types: deb
URIs: https://deb.debian.org/debian
Suites: sid
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

apt-get update
apt-get install -y pciutils || true

# Oxi OS branding (mirrors installer/branding/os-release).
cp /run/install/repo/oxios/os-release /etc/os-release 2>/dev/null || true
cp /run/install/repo/oxios/os-release /usr/lib/os-release 2>/dev/null || true
cp /run/install/repo/oxios/lsb-release /etc/lsb-release 2>/dev/null || true

# Installer payload drops the logo pack under /usr/share/oxios/branding;
# wire it into GNOME Settings -> About (LOGO=oxios resolves via hicolor).
BRAND=/usr/share/oxios/branding
if [ -d "$BRAND" ]; then
  for size in 16 32 48 64 128 256 512; do
    install -Dm644 "$BRAND/icons/oxios-${size}.png" \
      "/usr/share/icons/hicolor/${size}x${size}/apps/oxios.png"
  done
  install -Dm644 "$BRAND/icons/oxios-1024.png" \
    /usr/share/icons/hicolor/scalable/apps/oxios.png
  install -Dm644 "$BRAND/icons/oxios-256.png" /usr/share/pixmaps/oxios.png
  gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi

# Plymouth: enable the responsive oxios theme (logo top, spinner + bar below).
if [ -d /usr/share/plymouth/themes/oxios ]; then
  plymouth-set-default-theme -R oxios 2>/dev/null || \
    plymouth-set-default-theme oxios 2>/dev/null || true
  update-initramfs -u 2>/dev/null || true
fi

# GRUB: theme + quiet splash.
mkdir -p /etc/default/grub.d
cat > /etc/default/grub.d/99-oxios.cfg <<'EOF'
GRUB_THEME="/usr/share/grub/themes/oxios/theme.txt"
GRUB_TIMEOUT=5
GRUB_TIMEOUT_STYLE=menu
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_GFXMODE=auto
GRUB_GFXPAYLOAD_LINUX=keep
EOF
update-grub 2>/dev/null || true
%end

reboot
