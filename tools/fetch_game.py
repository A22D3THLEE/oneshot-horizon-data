#!/usr/bin/env python3
"""Downloads the Minecraft version research-lock.json pins, straight from Mojang, into the layout of
the official launcher's game folder (versions/, libraries/, assets/) plus server.jar, for
horizon-prepare --minecraft-dir. Every file is checked by SHA-1: the version JSON against the lock's
manifest_sha1, the jars against client_sha1/server_sha1, the rest against the version JSON.
Usage: fetch_game.py LOCK_JSON OUT_DIR"""
import concurrent.futures
import hashlib
import json
import os
import sys
import time
import urllib.request

AGENT = "oneshot-horizon-data (github actions)"


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url, path, want):
    """Downloads url to path unless path already has SHA-1 want; 4 tries."""
    if os.path.isfile(path) and sha1(path) == want:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".part"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as out:
                while block := r.read(1 << 20):
                    out.write(block)
            got = sha1(part)
            if got != want:
                raise ValueError(f"sha1 {got}, expected {want}")
            os.replace(part, path)
            return
        except Exception as e:  # noqa: BLE001 - every failure is retried, the last one raised
            if attempt == 3:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(2 + attempt * 3)


def safe(rel):
    rel = rel.replace("\\", "/")
    if rel.startswith("/") or any(p in ("", "..") for p in rel.split("/")):
        raise ValueError(f"unsafe path {rel!r}")
    return rel


def main():
    lock_path, out = sys.argv[1], sys.argv[2]
    lock = json.load(open(lock_path, encoding="utf-8"))["minecraft"]
    version = lock["version"]
    vdir = os.path.join(out, "versions", version)
    vjson = os.path.join(vdir, version + ".json")
    fetch(f"https://piston-meta.mojang.com/v1/packages/{lock['manifest_sha1']}/{version}.json",
          vjson, lock["manifest_sha1"])
    manifest = json.load(open(vjson, encoding="utf-8"))
    if manifest.get("id") != version:
        raise SystemExit(f"version JSON is {manifest.get('id')}, not {version}")
    client, server = manifest["downloads"]["client"], manifest["downloads"]["server"]
    if client["sha1"] != lock["client_sha1"] or server["sha1"] != lock["server_sha1"]:
        raise SystemExit("the version JSON's jars are not the pinned ones")

    jobs = [(client["url"], os.path.join(vdir, version + ".jar"), client["sha1"]),
            (server["url"], os.path.join(out, "server.jar"), server["sha1"])]
    # Every library artifact, whatever its OS rules: horizon-prepare picks the ones it needs.
    for lib in manifest.get("libraries", []):
        art = lib.get("downloads", {}).get("artifact")
        if art and art.get("url"):
            jobs.append((art["url"], os.path.join(out, "libraries", safe(art["path"])), art["sha1"]))
    index = manifest["assetIndex"]
    index_path = os.path.join(out, "assets", "indexes", safe(index["id"]) + ".json")
    fetch(index["url"], index_path, index["sha1"])
    objects = json.load(open(index_path, encoding="utf-8"))["objects"]
    hashes = sorted({o["hash"] for o in objects.values()})
    for h in hashes:
        if len(h) != 40 or any(c not in "0123456789abcdef" for c in h):
            raise SystemExit(f"bad asset hash {h!r}")
        jobs.append((f"https://resources.download.minecraft.net/{h[:2]}/{h}",
                     os.path.join(out, "assets", "objects", h[:2], h), h))

    print(f"{version}: {len(jobs)} files", flush=True)
    done = 0
    with concurrent.futures.ThreadPoolExecutor(16) as pool:
        for f in concurrent.futures.as_completed([pool.submit(fetch, *j) for j in jobs]):
            f.result()
            done += 1
            if done % 500 == 0:
                print(f"{done}/{len(jobs)}", flush=True)
    print(f"done: {done} files in {out}")


if __name__ == "__main__":
    main()
