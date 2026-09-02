#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# NVIDIA Driver Detection Module for Calamares
# Automatically detects NVIDIA hardware and installs proprietary drivers

import subprocess
import os
import shutil

def detect_nvidia_gpu():
    """Detect if NVIDIA GPU is present in the system."""
    try:
        result = subprocess.run(
            ['lspci', '-nn'],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout.lower()
        return 'nvidia' in output and ('vga' in output or '3d controller' in output or 'display controller' in output)
    except Exception:
        return False

def get_nvidia_pci_ids():
    """Get NVIDIA PCI IDs for driver matching."""
    try:
        result = subprocess.run(
            ['lspci', '-nn', '-d', '10de:'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""

def install_nvidia_drivers(target_root):
    """Install NVIDIA drivers in the target system."""
    try:
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        
        subprocess.run(
            ['chroot', target_root, 'apt-get', 'update'],
            check=True,
            env=env
        )
        
        subprocess.run(
            ['chroot', target_root, 'apt-get', 'install', '-y', '-t', 'trixie-backports',
             'nvidia-driver', 'nvidia-kernel-dkms', 'nvidia-settings', 'nvidia-xconfig'],
            check=True,
            env=env,
            timeout=300
        )
        
        subprocess.run(
            ['chroot', target_root, 'nvidia-xconfig', '--enable-all-gpus'],
            check=False,
            env=env
        )
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install NVIDIA drivers: {e}")
        return False
    except Exception as e:
        print(f"Error installing NVIDIA drivers: {e}")
        return False

def run():
    """Main entry point for Calamares module."""
    print("NVIDIA Driver Detection Module started")
    
    target_root = os.environ.get('TARGET_ROOT', '/target')
    
    if not os.path.exists(target_root):
        print(f"Target root {target_root} does not exist")
        return 1
    
    if detect_nvidia_gpu():
        print("NVIDIA GPU detected, installing proprietary drivers...")
        pci_ids = get_nvidia_pci_ids()
        print(f"NVIDIA PCI IDs: {pci_ids}")
        
        if install_nvidia_drivers(target_root):
            print("NVIDIA drivers installed successfully")
        else:
            print("Failed to install NVIDIA drivers")
            return 1
    else:
        print("No NVIDIA GPU detected, skipping driver installation")
    
    return 0

if __name__ == "__main__":
    exit(run())