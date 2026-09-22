"""User, locale, timezone and network step for the Oxi OS installer."""
from __future__ import annotations

import re
import subprocess


USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def valid_username(name: str) -> bool:
    return bool(USERNAME_RE.match(name or ""))


def password_ok(password: str, minimum: int = 1) -> bool:
    return len(password or "") >= minimum


def create_user(target: str, username: str, password: str, fullname: str = "") -> None:
    """Create *username* inside the installed system at *target*."""
    subprocess.run(
        ["chroot", target, "useradd", "-m", "-G", "sudo",
         "-c", fullname or username, "-s", "/bin/bash", username],
        check=True,
    )
    proc = subprocess.run(
        ["chroot", target, "chpasswd"],
        input=f"{username}:{password}", text=True, capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"chpasswd failed: {proc.stderr.strip()}")


def lock_root(target: str) -> None:
    subprocess.run(["chroot", target, "passwd", "--lock", "root"], check=False)


def set_locale(target: str, locale: str = "en_US.UTF-8") -> None:
    subprocess.run(["chroot", target, "update-locale", f"LANG={locale}"], check=False)
    with open(f"{target}/etc/locale.conf", "w", encoding="utf-8") as fh:
        fh.write(f"LANG={locale}\n")


def set_timezone(target: str, timezone: str = "Etc/UTC") -> None:
    zone = f"/usr/share/zoneinfo/{timezone}"
    subprocess.run(["chroot", target, "ln", "-sf", zone, "/etc/localtime"], check=False)
    with open(f"{target}/etc/timezone", "w", encoding="utf-8") as fh:
        fh.write(f"{timezone}\n")


def enable_services(target: str, services: tuple[str, ...] = ("gdm", "NetworkManager")) -> None:
    for service in services:
        subprocess.run(
            ["chroot", target, "systemctl", "enable", service], check=False)
