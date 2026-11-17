"""Share the fly-through render between this Mac and the Windows machine without rendering a frame twice.

The Windows Blender renders upwards (950, 951, ...) with "overwrite" off, so it skips any frame
whose file already exists when it gets there. This Mac takes frames from the top down
(2220, 2219, ...): before rendering one, it leaves an empty placeholder file of that name in the
Windows frames folder, which makes the Windows render skip it. The Mac stops taking frames once
it gets within two frames of the one Windows is working on.

    claim_frame.py           print the next frame for this Mac (and mark it on Windows), or nothing
    claim_frame.py release   drop the mark of a frame the Mac claimed but did not finish
"""
import os
import subprocess
import sys

ROOT = "/Users/dancostin/Downloads/Generate3D"
LOCAL = os.path.join(ROOT, "out", "flythrough", "frames")
STATE = os.path.join(ROOT, "logs", "claim_current")
SSH = ["ssh", "-p", "2121", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "danco@172.22.169.76"]
WIN = r"D:\apartment\out\flythrough\frames"
FIRST, LAST = 950, 2220


def remote(cmd):
    return subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=120).stdout


def name(f):
    return "f_{:04d}.png".format(f)


def release():
    if not os.path.exists(STATE):
        return
    f = int(open(STATE).read().strip() or 0)
    if f and not os.path.exists(os.path.join(LOCAL, name(f))):
        p = WIN + "\\" + name(f)
        # only an empty placeholder is ours to delete
        remote('powershell -NoProfile -Command "$f = Get-Item \'{0}\' -EA SilentlyContinue; '
               'if ($f -and $f.Length -eq 0) {{ Remove-Item \'{0}\' }}"'.format(p))
    os.remove(STATE)


def claim():
    release()
    listing = remote('powershell -NoProfile -Command "Get-ChildItem {} -Filter f_*.png | '
                     'ForEach-Object {{ $_.Name + \' \' + $_.Length }}"'.format(WIN))
    there, real = set(), []
    for line in listing.split("\n"):
        parts = line.split()
        if len(parts) == 2 and parts[0].startswith("f_"):
            f = int(parts[0][2:6])
            there.add(f)
            if int(parts[1]) > 0:
                real.append(f)
    if not listing.strip():
        return None                                  # Windows unreachable: better to stop than to guess
    floor = max(real or [FIRST - 1]) + 2            # Windows is rendering floor - 1 right now
    for f in range(LAST, floor, -1):
        if f in there or os.path.exists(os.path.join(LOCAL, name(f))):
            continue
        p = WIN + "\\" + name(f)
        if "ok" in remote('if not exist {0} (type nul > {0} && echo ok)'.format(p)):
            with open(STATE, "w") as fh:
                fh.write(str(f))
            return f
        return None
    return None


if __name__ == "__main__":
    if sys.argv[1:] == ["release"]:
        release()
    else:
        f = claim()
        print(f if f else "")
