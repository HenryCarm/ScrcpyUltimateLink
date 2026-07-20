#!/usr/bin/env python3
"""
Spawn external terminal for Nuitka compilation to avoid softlocking the current session.
Run this script to compile the PC app in a separate terminal window.
"""
import subprocess
import os
import platform

# Change to project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)

build_cmd = (
    "python3 -m nuitka --standalone --onefile --enable-plugin=pyqt6 "
    "--windows-icon-from-ico=scrcpy.ico --linux-icon=icon.png main.py"
)

print(f"Spawning external terminal for Nuitka compilation...")
print(f"Project directory: {project_dir}")
print(f"Build command: {build_cmd}")

if platform.system() == "Windows":
    # Spawns a new CMD window on Windows
    subprocess.Popen(f'start cmd /k "{build_cmd}"', shell=True)
elif platform.system() == "Darwin":
    # Spawns a new Terminal window on macOS
    subprocess.Popen(['open', '-a', 'Terminal', build_cmd])
else:
    # Spawns a new terminal window on Linux Mint / Ubuntu
    try:
        subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{build_cmd}; exec bash'])
    except FileNotFoundError:
        try:
            subprocess.Popen(['x-terminal-emulator', '-e', f'bash -c "{build_cmd}; exec bash"'])
        except FileNotFoundError:
            subprocess.Popen(['konsole', '-e', f'bash -c "{build_cmd}; exec bash"'])

print("Spawned external terminal for Nuitka compilation! You won't softlock now!")