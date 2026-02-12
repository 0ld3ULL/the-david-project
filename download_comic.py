"""
Download latest comic from VPS to local output folder.

Usage:
    python download_comic.py                    # Download latest comic
    python download_comic.py --list             # List all comics on VPS
    python download_comic.py <folder_name>      # Download specific comic
"""

import os
import subprocess
import sys

VPS = "root@89.167.24.222"
REMOTE_DIR = "/opt/david-flip/data/comics"
LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "comics")


def run(cmd):
    """Run a command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def list_comics():
    """List all comic folders on VPS."""
    out, rc = run(f'ssh {VPS} "ls -t {REMOTE_DIR}"')
    if rc != 0 or not out:
        print("No comics found on VPS (or SSH failed).")
        return []
    folders = out.strip().split("\n")
    print(f"\nComics on VPS ({len(folders)}):\n")
    for i, f in enumerate(folders, 1):
        print(f"  {i}. {f}")
    print()
    return folders


def download(folder_name):
    """Download a comic folder from VPS."""
    local_path = os.path.join(LOCAL_DIR, folder_name)
    os.makedirs(local_path, exist_ok=True)

    remote_path = f"{VPS}:{REMOTE_DIR}/{folder_name}/"

    print(f"\nDownloading: {folder_name}")
    print(f"  From: {remote_path}")
    print(f"  To:   {local_path}\n")

    # Use scp -r to download entire folder
    rc = subprocess.call(f'scp -r {remote_path}* "{local_path}/"', shell=True)

    if rc == 0:
        print(f"\nDone! Files saved to:\n  {local_path}\n")
        # List what was downloaded
        print("Contents:")
        for root, dirs, files in os.walk(local_path):
            depth = root.replace(local_path, "").count(os.sep)
            indent = "  " * (depth + 1)
            for f in sorted(files):
                size = os.path.getsize(os.path.join(root, f))
                if size > 1_000_000:
                    size_str = f"{size / 1_000_000:.1f} MB"
                elif size > 1_000:
                    size_str = f"{size / 1_000:.0f} KB"
                else:
                    size_str = f"{size} B"
                subdir = os.path.basename(root) if root != local_path else ""
                prefix = f"{subdir}/" if subdir else ""
                print(f"{indent}{prefix}{f}  ({size_str})")
        print()

        # Open folder in Explorer
        os.startfile(local_path)
    else:
        print("\nDownload failed. Check SSH connection.")


def main():
    if "--list" in sys.argv:
        list_comics()
        return

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        download(args[0])
    else:
        # Get latest comic
        out, rc = run(f'ssh {VPS} "ls -t {REMOTE_DIR} | head -1"')
        if rc != 0 or not out:
            print("No comics found on VPS (or SSH failed).")
            print("Try: python download_comic.py --list")
            return
        download(out.strip())


if __name__ == "__main__":
    main()
