#!/usr/bin/env python3
"""X11 window screenshot helper for GUI-doc figures.

Finds a window by title (substring match via xdotool search --name),
grabs the X display via Pillow ImageGrab, crops to the window geometry,
saves PNG. Fallback: full-screen grab with manual crop box.

Usage:
  python3 tools/x11_shot.py --name "SHOT_X" --out docs/figures/foo.png
  python3 tools/x11_shot.py --fullscreen --out docs/figures/foo.png --crop X,Y,W,H
"""
import argparse
import subprocess
import sys
import time

from PIL import ImageGrab

DISPLAY = ":1"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def find_window(name):
    r = run(["xdotool", "search", "--name", name])
    ids = [l for l in r.stdout.strip().split("\n") if l]
    if not ids:
        return None, None
    wid = ids[-1]  # newest match
    g = run(["xdotool", "getwindowgeometry", "--shell", wid])
    geo = {}
    for line in g.stdout.strip().split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            geo[k.strip()] = int(v.strip())
    return wid, geo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", help="window title substring to search")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--crop", help="X,Y,W,H for fullscreen crops")
    ap.add_argument("--wait", type=float, default=1.0, help="seconds to wait before grab")
    args = ap.parse_args()

    time.sleep(args.wait)

    if args.fullscreen:
        im = ImageGrab.grab(xdisplay=DISPLAY)
        if args.crop:
            x, y, w, h = [int(v) for v in args.crop.split(",")]
            im = im.crop((x, y, x + w, y + h))
    else:
        wid, geo = find_window(args.name)
        if not geo:
            print(f"ERROR: window '{args.name}' not found", file=sys.stderr)
            sys.exit(1)
        im = ImageGrab.grab(xdisplay=DISPLAY)
        x, y = geo.get("X", 0), geo.get("Y", 0)
        w, h = geo.get("WIDTH", 800), geo.get("HEIGHT", 600)
        # margin for window decorations/title bar
        im = im.crop((max(0, x - 4), max(0, y - 4), x + w + 4, y + h + 4))

    im.save(args.out)
    print(f"saved {args.out} ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
