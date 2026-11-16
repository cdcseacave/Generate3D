#!/usr/bin/env python3
"""Fetch photo-scanned household objects from Google's "Scanned Objects" collection
(Google Research, CC-BY 4.0), served without an account by Gazebo Fuel.

    tools/fetch_gso.py list [regex]        refresh the catalogue, print matching names
    tools/fetch_gso.py get NAME [NAME...]  download and unpack into assets/gso/NAME/

Each model unpacks to meshes/model.obj (metres, Z up... see apartment/gso.py) and
materials/textures/texture.png."""
import io
import json
import os
import re
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "assets", "gso")
CAT = os.path.join(ROOT, "assets", "_catalog", "gso.json")
API = "https://fuel.gazebosim.org/1.0/GoogleResearch/models"
UA = {"User-Agent": "apartment-generator/1.0"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def catalogue(refresh=False):
    if os.path.exists(CAT) and not refresh:
        return json.load(open(CAT))
    out, page = [], 1
    while True:
        d = json.loads(_get("{}?page={}&per_page=100".format(API, page)))
        if not d:
            break
        out += [{"name": m["name"], "size": m.get("filesize", 0), "desc": m.get("description", ""),
                 "cats": m.get("categories", []), "tags": m.get("tags", [])} for m in d]
        if len(d) < 100:
            break
        page += 1
    os.makedirs(os.path.dirname(CAT), exist_ok=True)
    json.dump(out, open(CAT, "w"))
    return out


def get(name):
    dst = os.path.join(DEST, name)
    if os.path.exists(os.path.join(dst, "meshes", "model.obj")):
        return "have"
    data = _get("{}/{}/1/{}.zip".format(API, name, name))
    os.makedirs(dst, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for m in z.infolist():
            p = os.path.normpath(m.filename)
            if p.startswith("..") or os.path.isabs(p) or m.is_dir():
                continue
            if not re.search(r"\.(obj|mtl|png|jpg|jpeg|sdf|config|pbtxt)$", p, re.I):
                continue
            full = os.path.join(dst, p)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(z.read(m))
    return "{:.1f} MB".format(len(data) / 1e6)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        rx = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
        for m in catalogue(refresh=not os.path.exists(CAT)):
            if rx is None or rx.search(m["name"]) or rx.search(m["desc"] or ""):
                print("{:60s} {:5.1f} MB  {}".format(m["name"], m["size"] / 1e6, ",".join(m["cats"] or [])))
    elif cmd == "get":
        for n in sys.argv[2:]:
            try:
                print(n, get(n))
            except Exception as e:
                print(n, "FAILED", repr(e))
