#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
icon_port.py - copies item icons from the atlases of other mods (OGSM, SGM) into a copy of the SRP atlas.

    python3 icon_port.py --base <core ui_icon_equipment.dds> --ogsm <csogsm ...dds> --sgm <sgm ...dds> [--apply] [--dry]

The map is icon_port.json: for every icon the source atlas, the source cell (x, y, w, h in 50x50 px cells), the target
cell in our atlas and the sections that use it (file, section). Without --apply only the atlas is written
(gamedata/textures/ui/ui_icon_equipment.dds of the addon); with --apply the inv_grid_x / y / width / height of the listed
sections are rewritten to the target cell. The target area must be free (transparent) in the base atlas, otherwise the
tool stops. The addon's atlas is a COPY of the core one: when the core atlas changes, run the tool again.
Needs Pillow. Icons are taken from OGSM Extended 2.0 and SGM 3.10 (authors in the module headers of the addon).
"""
import argparse, json, os, re, sys
from PIL import Image

CELL = 50
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISC = os.path.join(ROOT, "gamedata", "configs", "misc")


def drawn(im, x, y, w, h):
    px = im.crop((x * CELL, y * CELL, (x + w) * CELL, (y + h) * CELL)).getchannel("A").tobytes()
    return sum(1 for v in px if v > 16) / max(1, len(px))


def set_grid(section, cell):
    x, y, w, h = cell
    for fn in os.listdir(MISC):
        if not fn.endswith(".ltx"):
            continue
        p = os.path.join(MISC, fn)
        raw = open(p, "rb").read()
        text = raw.decode("cp1251")
        m = re.search(r"(?m)^\[" + re.escape(section) + r"\][^\r\n]*\r?\n", text)
        if not m:
            continue
        nxt = re.search(r"(?m)^\[", text[m.end():])
        end = m.end() + (nxt.start() if nxt else len(text) - m.end())
        body = text[m.end():end]
        for key, val in (("inv_grid_x", x), ("inv_grid_y", y), ("inv_grid_width", w), ("inv_grid_height", h)):
            pat = re.compile(r"(?m)^(" + key + r"\s*=\s*)\d+")
            if pat.search(body):
                body = pat.sub(lambda mm: mm.group(1) + str(val), body, count=1)
            else:
                eol = "\r\n" if "\r\n" in text else "\n"
                body = body.rstrip("\r\n") + eol + "%s = %d" % (key, val) + eol + (eol if body.endswith(eol + eol) else "")
        text = text[:m.end()] + body + text[end:]
        open(p, "wb").write(text.encode("cp1251"))
        return fn
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--ogsm", required=True)
    ap.add_argument("--sgm", required=True)
    ap.add_argument("--map", default=os.path.join(ROOT, "tools", "icon_port.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "gamedata", "textures", "ui", "ui_icon_equipment.dds"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    base = Image.open(a.base).convert("RGBA")
    src = {"ogsm": Image.open(a.ogsm).convert("RGBA"), "sgm": Image.open(a.sgm).convert("RGBA")}
    out = base.copy()
    taken = []
    bad = 0
    for e in json.load(open(a.map)):
        sx, sy, w, h = e["from"]
        tx, ty = e["to"]
        d = drawn(src[e["src"]], sx, sy, w, h)
        free = drawn(base, tx, ty, w, h)
        clash = [t for t in taken if not (tx + w <= t[0] or t[0] + t[2] <= tx or ty + h <= t[1] or t[1] + t[3] <= ty)]
        msg = "%-28s %s(%d,%d %dx%d) drawn %3d%% -> (%d,%d)" % (e["name"], e["src"], sx, sy, w, h, d * 100, tx, ty)
        if d < 0.05:
            msg += "  !! SOURCE IS EMPTY"; bad += 1
        if free > 0.02:
            msg += "  !! TARGET NOT FREE (%d%% drawn)" % (free * 100); bad += 1
        if clash:
            msg += "  !! OVERLAPS ANOTHER ICON"; bad += 1
        taken.append((tx, ty, w, h))
        print(msg)
        out.paste(src[e["src"]].crop((sx * CELL, sy * CELL, (sx + w) * CELL, (sy + h) * CELL)), (tx * CELL, ty * CELL))
    if bad:
        sys.exit("stopped: %d problem(s) above" % bad)
    if a.dry:
        return
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out.save(a.out, pixel_format="DXT3")
    print("atlas written:", a.out)
    if a.apply:
        for e in json.load(open(a.map)):
            sx, sy, w, h = e["from"]
            for s in e["sections"]:
                print("  %-30s -> %s" % (s, set_grid(s, (e["to"][0], e["to"][1], w, h)) or "SECTION NOT FOUND"))


if __name__ == "__main__":
    main()
