#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
soc_tasks_to_ltx.py - converts Shadow of Chernobyl game_task XML (configs/gameplay/tasks.xml) to the Freeplay
fp_tasks format (misc/fp_tasks.ltx).

    python3 soc_tasks_to_ltx.py tasks.xml [-o fp_tasks.ltx] [--sid-map sid_map.json] [--known-infos infos.txt]
                                [--only id1,id2] [--report report.txt]

Mapping of one <objective> to one stage:
    <text>                    -> text_N          (string id; falls back to the task title)
    <map_location_type hint>  -> spot_N, hint_N  (SoC green/blue/... -> CS spot type, see SPOTS)
    <map_location_hidden>1    -> hidden_N = true
    <object_story_id>         -> target_N        (SoC string id; numbers come from --sid-map or [sid_map] of the ltx)
    <infoportion_complete>    -> complete_N      +info
    <function_complete>       -> complete_N      =name   (module prefix dropped; implement it in fp_task_funcs.script)
    <infoportion_fail>        -> fail_N          +info
    <function_fail>           -> fail_N          =name
    <infoportion_set_complete>-> on_complete_N   +info
    <infoportion_set_fail>    -> on_fail         +info   (task level)
    <icon>, <article>         -> kept as comments (the CS UI has no such icons / encyclopedia links yet)
Several conditions of one kind in one objective are joined as AND.
The report lists what the converted file still needs: info portions, functions, story ids, string ids.
"""
import argparse, json, re, sys
import xml.etree.ElementTree as ET

SPOTS = {  # SoC map spot -> CS map spot (stock ones of the CS UI)
    "green_location": "secondary_task_location",
    "blue_location": "secondary_task_location",
    "red_location": "secondary_task_location",
    "storyline_task_location": "storyline_task_location",
}
DEFAULT_SPOT = "secondary_task_location"


def read_xml(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "cp1251"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    text = re.sub(r"<\?xml[^>]*\?>", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # the engine tolerates '--' inside comments, XML parsers do not
    return ET.fromstring("<root>" + text + "</root>")


def texts(o, tag):
    return [(e.text or "").strip() for e in o.findall(tag) if (e.text or "").strip()]


def cond(infos, funcs, rep_infos, rep_funcs):
    parts = ["+" + i for i in infos]
    rep_infos.update(infos)
    for f in funcs:
        name = f.split(".")[-1]
        parts.append("=" + name)
        rep_funcs[name] = f
    return " ".join(parts)


def convert(root, only, sid_map, known, rep):
    out = []
    for g in root.iter("game_task"):
        tid = g.get("id")
        if only and tid not in only:
            continue
        title = (g.findtext("title") or tid).strip()
        objs = g.findall("objective")
        rep["strings"].add(title)
        out.append("[%s]" % tid)
        out.append("kind = storyline")
        out.append("title = %s" % title)
        out.append("prio = %s" % (g.get("prio") or "0"))
        out.append("count = %d" % len(objs))
        on_fail = []
        for n, o in enumerate(objs, 1):
            text = (o.findtext("text") or "").strip() or title
            rep["strings"].add(text)
            out.append("text_%d = %s" % (n, text))
            ic = (o.findtext("icon") or "").strip()
            art = (o.findtext("article") or "").strip()
            if ic or art:
                out.append("; icon_%d = %s  article_%d = %s" % (n, ic, n, art))
            mt = o.find("map_location_type")
            sid = (o.findtext("object_story_id") or "").strip()
            if mt is not None:
                spot = SPOTS.get((mt.text or "").strip(), DEFAULT_SPOT)
                out.append("spot_%d = %s" % (n, spot))
                if mt.get("hint"):
                    out.append("hint_%d = %s" % (n, mt.get("hint")))
                    rep["strings"].add(mt.get("hint"))
            if sid:
                out.append("target_%d = %s" % (n, sid))
                rep["sids"].add(sid)
            if (o.findtext("map_location_hidden") or "").strip() in ("1", "true"):
                out.append("hidden_%d = true" % n)
            c = cond(texts(o, "infoportion_complete"), texts(o, "function_complete"), rep["infos"], rep["funcs"])
            f = cond(texts(o, "infoportion_fail"), texts(o, "function_fail"), rep["infos"], rep["funcs"])
            s = texts(o, "infoportion_set_complete")
            rep["infos"].update(s)
            if c:
                out.append("complete_%d = %s" % (n, c))
            elif n == len(objs):
                out.append("; stage %d has no completion condition: finish it with fp_tasks.complete(\"%s\")" % (n, tid))
            if f:
                out.append("fail_%d = %s" % (n, f))
            if s:
                out.append("on_complete_%d = %s" % (n, " ".join("+" + i for i in s)))
            on_fail += texts(o, "infoportion_set_fail")
        if on_fail:
            rep["infos"].update(on_fail)
            out.append("on_fail = " + " ".join("+" + i for i in on_fail))
        out.append("")
    # sid map
    out.append("[sid_map]")
    for sid in sorted(rep["sids"]):
        if sid in sid_map:
            out.append("%s = %s" % (sid, sid_map[sid]))
        else:
            out.append(";%s = <CS story id>" % sid)
    out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xml")
    ap.add_argument("-o", "--out")
    ap.add_argument("--sid-map")
    ap.add_argument("--known-infos", help="text file: info portion ids that already exist in CS, one per line")
    ap.add_argument("--only")
    ap.add_argument("--report")
    a = ap.parse_args()
    sid_map = json.load(open(a.sid_map)) if a.sid_map else {}
    known = set(l.strip() for l in open(a.known_infos)) if a.known_infos else set()
    rep = {"infos": set(), "funcs": {}, "sids": set(), "strings": set()}
    only = set(a.only.split(",")) if a.only else None
    ltx = convert(read_xml(a.xml), only, sid_map, known, rep)
    if a.out:
        open(a.out, "w", encoding="cp1251", newline="\r\n").write(ltx)
    else:
        sys.stdout.write(ltx)
    r = []
    new_infos = sorted(rep["infos"] - known)
    r.append("info portions needed (%d, not in --known-infos): add to info_portions.xml:" % len(new_infos))
    r += ['\t<info_portion id="%s"/>' % i for i in new_infos]
    r.append("functions to implement in fp_task_funcs.script (%d):" % len(rep["funcs"]))
    r += ["\t%s   <- %s" % (k, v) for k, v in sorted(rep["funcs"].items())]
    miss = sorted(s for s in rep["sids"] if s not in sid_map)
    r.append("story ids without a CS number (%d):" % len(miss))
    r += ["\t" + s for s in miss]
    r.append("string ids to translate (%d):" % len(rep["strings"]))
    r += ["\t" + s for s in sorted(rep["strings"])]
    (open(a.report, "w", encoding="utf-8").write("\n".join(r) + "\n") if a.report else sys.stderr.write("\n".join(r) + "\n"))


if __name__ == "__main__":
    main()
