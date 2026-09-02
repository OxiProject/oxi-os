#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Backports Kernel Module for Calamares
# Installs the latest kernel from Debian backports

import subprocess
import os

def run():
    """Main entry point for Calamares module."""
    print("Backports Kernel Module started")
    
    target_root = os.environ.get('TARGET_ROOT', '/target')
    
    if not os.path.exists(target_root):
        print(f"Target root {target_root} does not exist")
        return 1
    
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
             'linux-image-amd64', 'linux-headers-amd64'],
            check=True,
            env=env,
            timeout=300
        )
        
        subprocess.run(
            ['chroot', target_root, 'update-initramfs', '-u'],
            check=True,
            env=env
        )
        
        subprocess.run(
            ['chroot', target_root, 'update-grub'],
            check=True,
            env=env
        )
        
        print("Backports kernel installed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Failed to install backports kernel: {e}")
        return 1
    except Exception as e:
        print(f"Error installing backports kernel: {e}")
        return 1

if __name__ == "__main__":
    exit(run())