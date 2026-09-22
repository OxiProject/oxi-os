"""GTK/Adwaita front-end for the Oxi OS installer (Anaconda-style hub)."""
from __future__ import annotations

import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .partitioning import ROOT_FS, Plan, list_disks  # noqa: E402
from . import install as backend  # noqa: E402
from . import usersetup  # noqa: E402

APP_ID = "org.oxios.Installer"
BRANDING_DIR = os.environ.get(
    "OXIOS_BRANDING_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "..", "branding"),
)
DEFAULT_PACKAGES = [
    "gnome", "gnome-shell", "gnome-session", "gnome-control-center",
    "gnome-terminal", "nautilus", "gdm3", "gnome-software",
    "gnome-text-editor", "gnome-calculator", "gnome-system-monitor",
    "gnome-disk-utility", "gnome-tweaks", "network-manager",
    "pipewire", "wireplumber", "pipewire-audio", "pipewire-pulse",
    "flatpak", "xfsprogs", "plymouth", "plymouth-themes",
    "linux-image-amd64", "sudo", "bash-completion", "curl",
    "ca-certificates", "os-prober", "firmware-linux",
    "firmware-linux-free", "firmware-sof-signed",
]


class InstallerWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Oxi OS Installer")
        self.set_default_size(900, 640)

        self.disks = list_disks()
        self.selected_disk: str = self.disks[0]["path"] if self.disks else ""
        self.encrypt = False
        self.timezone = "Etc/UTC"
        self.installing = False

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self._build_hub()
        self._build_user_page()
        self._build_progress_page()

        header = Adw.HeaderBar()
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self.stack)
        self.set_content(toolbar)

    # -- hub page ---------------------------------------------------------
    def _build_hub(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        logo_path = os.path.join(BRANDING_DIR, "icons", "oxios-256.png")
        if os.path.exists(logo_path):
            logo = Gtk.Image.new_from_file(logo_path)
            logo.set_pixel_size(128)
            box.append(logo)

        title = Gtk.Label(label="Install Oxi OS")
        title.add_css_class("title-1")
        box.append(title)
        sub = Gtk.Label(label=f"Debian Sid · GNOME · {ROOT_FS.upper()} root")
        sub.add_css_class("dim-label")
        box.append(sub)

        group = Adw.PreferencesGroup(title="Installation destination")
        row = Adw.ComboRow(title="Target disk",
                           subtitle="All data on this disk will be erased")
        store = Gtk.StringList()
        for disk in self.disks:
            label = disk.get("label") or (
                f"{disk['path']} — {disk['model']} ({disk['size'] / 1e9:.0f} GB)")
            store.append(f"{disk['path']} · {label}")
        if not self.disks:
            store.append("No disks found")
        row.set_model(store)
        row.connect("notify::selected", self._on_disk_selected)
        group.add(row)

        self.encrypt_row = Adw.SwitchRow(
            title="Encrypt system",
            subtitle="LUKS-encrypt the XFS root partition")
        self.encrypt_row.connect("notify::active", self._on_encrypt_toggled)
        group.add(self.encrypt_row)

        fs_row = Adw.ActionRow(title="Root filesystem", subtitle=f"{ROOT_FS} (fixed)")
        fs_row.add_suffix(Gtk.Label(label=ROOT_FS.upper()))
        group.add(fs_row)
        box.append(group)

        tz_group = Adw.PreferencesGroup(title="Timezone")
        self.tz_entry = Adw.EntryRow(title="Timezone")
        self.tz_entry.set_text(self.timezone)
        self.tz_entry.connect("changed", self._on_tz_changed)
        tz_group.add(self.tz_entry)
        box.append(tz_group)

        self.hub_error = Gtk.Label(label="")
        self.hub_error.add_css_class("error")
        box.append(self.hub_error)

        next_btn = Gtk.Button(label="Continue")
        next_btn.add_css_class("suggested-action")
        next_btn.connect("clicked", self._on_hub_continue)
        box.append(next_btn)

        self.stack.add_named(box, "hub")

    # -- user page --------------------------------------------------------
    def _build_user_page(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        title = Gtk.Label(label="Create your account")
        title.add_css_class("title-1")
        box.append(title)

        group = Adw.PreferencesGroup()
        self.name_entry = Adw.EntryRow(title="Full name")
        self.user_entry = Adw.EntryRow(title="Username")
        self.pass_entry = Adw.PasswordEntryRow(title="Password")
        self.pass2_entry = Adw.PasswordEntryRow(title="Confirm password")
        for row in (self.name_entry, self.user_entry,
                    self.pass_entry, self.pass2_entry):
            group.add(row)
        box.append(group)

        self.user_error = Gtk.Label(label="")
        self.user_error.add_css_class("error")
        box.append(self.user_error)

        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        back = Gtk.Button(label="Back")
        back.connect("clicked", lambda _b: self.stack.set_visible_child_name("hub"))
        install_btn = Gtk.Button(label="Install Oxi OS")
        install_btn.add_css_class("suggested-action")
        install_btn.connect("clicked", self._on_install_clicked)
        btns.append(back)
        btns.append(install_btn)
        box.append(btns)

        self.stack.add_named(box, "user")

    # -- progress page ----------------------------------------------------
    def _build_progress_page(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(48)
        box.set_margin_bottom(48)
        box.set_margin_start(48)
        box.set_margin_end(48)
        box.set_valign(Gtk.Align.CENTER)

        self.status_label = Gtk.Label(label="Preparing…")
        self.status_label.add_css_class("title-2")
        box.append(self.status_label)
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        box.append(self.progress)
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_vexpand(True)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(220)
        scroll.set_child(self.log_view)
        box.append(scroll)
        self.done_btn = Gtk.Button(label="Reboot")
        self.done_btn.set_sensitive(False)
        self.done_btn.connect("clicked", self._on_reboot)
        box.append(self.done_btn)

        self.stack.add_named(box, "progress")

    # -- handlers ---------------------------------------------------------
    def _on_disk_selected(self, row: Adw.ComboRow, _pspec) -> None:
        if self.disks:
            self.selected_disk = self.disks[row.get_selected()]["path"]

    def _on_encrypt_toggled(self, row: Adw.SwitchRow, _pspec) -> None:
        self.encrypt = row.get_active()

    def _on_tz_changed(self, _row) -> None:
        self.timezone = self.tz_entry.get_text().strip() or "Etc/UTC"

    def _on_hub_continue(self, _btn) -> None:
        if not self.selected_disk:
            self.hub_error.set_text("No target disk available.")
            return
        self.hub_error.set_text("")
        self.stack.set_visible_child_name("user")

    def _on_install_clicked(self, _btn) -> None:
        username = self.user_entry.get_text().strip()
        password = self.pass_entry.get_text()
        confirm = self.pass2_entry.get_text()
        if not usersetup.valid_username(username):
            self.user_error.set_text("Invalid username (lowercase, _ - allowed).")
            return
        if not usersetup.password_ok(password):
            self.user_error.set_text("Password must not be empty.")
            return
        if password != confirm:
            self.user_error.set_text("Passwords do not match.")
            return
        self.user_error.set_text("")
        self.stack.set_visible_child_name("progress")
        threading.Thread(target=self._run_install,
                         args=(username, password,
                               self.name_entry.get_text().strip()),
                         daemon=True).start()

    def _log(self, message: str) -> None:
        buf = self.log_view.get_buffer()
        buf.insert(buf.get_end_iter(), message + "\n")

    def _on_progress(self, fraction: float, message: str) -> None:
        GLib.idle_add(self.progress.set_fraction, fraction)
        GLib.idle_add(self.status_label.set_text, message)
        GLib.idle_add(self._log, message)

    def _run_install(self, username: str, password: str, fullname: str) -> None:
        try:
            target = "/mnt/oxios-install"
            plan = Plan(disk=self.selected_disk, encrypt=self.encrypt)
            backend.prepare_disk(plan, target, self._on_progress)
            backend.bootstrap(target, self._on_progress)
            backend.install_packages(target, DEFAULT_PACKAGES, self._on_progress)
            GLib.idle_add(self._log, "Applying Oxi OS branding…")
            backend.apply_branding(target, BRANDING_DIR)
            GLib.idle_add(self._log, "Configuring boot (GRUB + Plymouth)…")
            backend.configure_boot(target, plan)
            backend.finish(target, username, password, fullname,
                           self.timezone, self._on_progress)
            GLib.idle_add(self._install_done, True, "Installation complete.")
        except Exception as exc:  # noqa: BLE001
            GLib.idle_add(self._install_done, False, f"Install failed: {exc}")

    def _install_done(self, ok: bool, message: str) -> None:
        self.status_label.set_text(message)
        self._log(message)
        self.progress.set_fraction(1.0 if ok else 0.0)
        self.done_btn.set_sensitive(ok)

    def _on_reboot(self, _btn) -> None:
        import subprocess  # noqa: PLC0415
        subprocess.run(["systemctl", "reboot"], check=False)


class InstallerApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self) -> None:
        win = InstallerWindow(self)
        win.present()


def main() -> None:
    app = InstallerApp()
    app.run([])
