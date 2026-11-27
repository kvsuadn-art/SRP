#!/usr/bin/env python3
# Freeplay extras: checks that the spawn menu cache (gamedata/configs/spawn_list.ltx) lists every
# spawnable section the addon defines. The in-game scan (collect_sections) only works on unpacked
# configs, so the shipped cache is the real list; a section missing here cannot be spawned for tests.
#
# Spawnable = the section (or one of its parents) has a "$spawn" key. Parents are resolved across
# the addon and the core gamedata. Only sections DEFINED in the addon are checked.
#
# Usage: python3 addons/freeplay_extras/tools/check_spawn_list.py   (from the repo root; exit 1 if something is missing)
# Adaptation for SRP Freeplay: Eon
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ADDON = os.path.join(ROOT, "addons", "freeplay_extras", "gamedata", "configs")
CORE = os.path.join(ROOT, "gamedata", "configs")
CACHE = os.path.join(ADDON, "spawn_list.ltx")
# sections that are spawnable by the rule above but must not be in the menu
IGNORE = {
    "skill_book",                                   # base section of the skill books
    "electro_chimera", "psy_burer",                 # defined in m_*.ltx copies but not used by fp_squads
    "zombie_kamikaze", "zombie_plague",             # (visuals and behaviour not verified)
}
HEAD = re.compile(r"^\s*\[([^\]]+)\]\s*(?::\s*([^;]*))?")

def read_sections(base):
    out = {}
    for d, _, files in os.walk(base):
        for f in files:
            if not f.endswith(".ltx"):
                continue
            cur = None
            for line in open(os.path.join(d, f), encoding="latin1"):
                line = line.split(";", 1)[0]
                m = HEAD.match(line)
                if m:
                    parents = [p.strip() for p in (m.group(2) or "").split(",") if p.strip()]
                    cur = out.setdefault(m.group(1).strip(), {"parents": parents, "spawn": False})
                elif cur is not None and line.strip().startswith("$spawn"):
                    cur["spawn"] = True
    return out

core, addon = read_sections(CORE), read_sections(ADDON)
allsec = dict(core); allsec.update(addon)

def spawnable(name, seen=()):
    s = allsec.get(name)
    if s is None or name in seen:
        return False
    return s["spawn"] or any(spawnable(p, seen + (name,)) for p in s["parents"])

cache = set()
for line in open(CACHE, encoding="latin1"):
    line = line.strip()
    if line and not line.startswith("["):
        cache.add(line)

missing = sorted(n for n in addon if n not in core and spawnable(n) and n not in cache and n not in IGNORE)
for n in missing:
    print("missing in spawn_list.ltx:", n)
print("checked %d addon sections, missing %d" % (len(addon), len(missing)))
sys.exit(1 if missing else 0)
