#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
icon_audit.py - table of the inventory icons of the Freeplay Extras items and a check of the atlas cells.

    python3 icon_audit.py [--atlas path/to/ui_icon_equipment.dds] [--out docs/icons.md] [--preview docs/icons_preview.png]

For every section with inv_grid_x in gamedata/configs/misc/*.ltx of the addon it prints: file, section, the cell
(x, y, width, height in 50x50 px cells of the atlas) and how much of that area is drawn (not transparent) in the atlas.
Status: EMPTY (nothing drawn there: the item shows no icon), SHARED (the same cell is used by several sections:
a placeholder), OK. A section without its own inv_grid_x inherits it from the parent (shown as INHERITS).
Needs Pillow (pip install pillow).
"""
import argparse, glob, os, re, sys
from collections import defaultdict
from PIL import Image, ImageDraw

CELL = 50
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse(path):
    secs, cur = {}, None
    for line in open(path, encoding="cp1251", errors="replace"):
        line = line.split(";")[0].strip()
        if not line:
            continue
        m = re.match(r"^\[([^\]]+)\]\s*(?::\s*(\S+))?", line)
        if m:
            cur = {"name": m.group(1), "parent": m.group(2), "f": {}}
            secs[m.group(1)] = cur
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            cur["f"][k.strip()] = v.strip()
    return secs


def drawn(im, x, y, w, h):
    c = im.crop((x * CELL, y * CELL, (x + w) * CELL, (y + h) * CELL)).getchannel("A")
    px = c.tobytes()
    return sum(1 for v in px if v > 16) / max(1, len(px))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", default=os.path.join(ROOT, "..", "..", "gamedata", "textures", "ui", "ui_icon_equipment.dds"))
    ap.add_argument("--out")
    ap.add_argument("--preview")
    a = ap.parse_args()
    im = Image.open(a.atlas).convert("RGBA")
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "gamedata", "configs", "misc", "*.ltx"))):
        secs = parse(path)
        for n, s in secs.items():
            f = s["f"]
            if "inv_grid_x" not in f:
                if s["parent"] and s["parent"] in secs and "inv_grid_x" in secs[s["parent"]]["f"]:
                    rows.append((os.path.basename(path), n, None, "INHERITS " + s["parent"], f.get("inv_name", "")))
                continue
            x, y = int(f["inv_grid_x"]), int(f["inv_grid_y"])
            w, h = int(f.get("inv_grid_width", 1)), int(f.get("inv_grid_height", 1))
            rows.append((os.path.basename(path), n, (x, y, w, h), None, f.get("inv_name", "")))
    users = defaultdict(list)
    for r in rows:
        if r[2]:
            users[r[2]].append(r[1])
    out = ["| file | section | cell x,y | size | drawn | status | inv_name |", "|---|---|---|---|---|---|---|"]
    stat = defaultdict(int)
    for fn, n, cell, note, name in rows:
        if cell is None:
            out.append("| %s | %s | - | - | - | %s | %s |" % (fn, n, note, name))
            continue
        x, y, w, h = cell
        d = drawn(im, x, y, w, h)
        st = "EMPTY" if d < 0.05 else ("SHARED(%d)" % len(users[cell]) if len(users[cell]) > 1 else "OK")
        stat[st.split("(")[0]] += 1
        out.append("| %s | %s | %d,%d | %dx%d | %d%% | %s | %s |" % (fn, n, x, y, w, h, round(d * 100), st, name))
    text = "\n".join(out)
    head = "Atlas: %dx%d px, cell %d px. Sections with their own cell: %s\n\n" % (im.size[0], im.size[1], CELL, dict(stat))
    if a.out:
        open(a.out, "w", encoding="utf-8", newline="\n").write(head + text + "\n")
    else:
        print(head + text)
    # map of the atlas: which cells have something drawn (to find free places for new icons)
    cols, rws = im.size[0] // CELL, im.size[1] // CELL
    used = [[drawn(im, cx, cy, 1, 1) > 0.02 for cx in range(cols)] for cy in range(rws)]
    mark = [[" "] * cols for _ in range(rws)]
    for cell, names in users.items():
        x, y, w, h = cell
        for cy in range(y, min(rws, y + h)):
            for cx in range(x, min(cols, x + w)):
                mark[cy][cx] = "A"
    lines = ["     " + "".join("%-3d" % c for c in range(cols))]
    for cy in range(rws):
        lines.append("%3d  " % cy + "".join(("#" if used[cy][cx] else ".") + ("*" if mark[cy][cx] == "A" else " ") + " " for cx in range(cols)))
    amap = "\n".join(lines)
    if a.out:
        open(a.out, "a", encoding="utf-8", newline="\n").write(
            "\n## Atlas map\n\n`#` = something is drawn in the cell, `.` = free (transparent), `*` = a cell used by one of our sections\n\n```\n" + amap + "\n```\n")
    else:
        print(amap)
    if a.preview:
        cells = sorted(users, key=lambda c: (c[1], c[0]))
        sc, W, pad = 2, 1400, 6
        x0 = y0 = pad
        rowh = 0
        tiles = []
        for c in cells:
            x, y, w, h = c
            tw, th = max(w * CELL * sc, 110), h * CELL * sc + 18
            if x0 + tw > W:
                x0, y0, rowh = pad, y0 + rowh + pad, 0
            tiles.append((c, x0, y0))
            x0 += tw + pad
            rowh = max(rowh, th)
        sheet = Image.new("RGBA", (W, y0 + rowh + pad), (40, 40, 40, 255))
        dr = ImageDraw.Draw(sheet)
        for c, ox, oy in tiles:
            x, y, w, h = c
            cr = im.crop((x * CELL, y * CELL, (x + w) * CELL, (y + h) * CELL)).resize((w * CELL * sc, h * CELL * sc))
            sheet.paste(cr, (ox, oy), cr)
            dr.rectangle((ox, oy, ox + max(w * CELL * sc, 110) - 1, oy + h * CELL * sc - 1), outline=(90, 90, 90, 255))
            dr.text((ox, oy + h * CELL * sc + 2), "%d,%d %dx%d %s" % (x, y, w, h, users[c][0][:16]), fill=(255, 255, 255, 255))
        sheet.save(a.preview)


if __name__ == "__main__":
    main()
