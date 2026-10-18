#!/usr/bin/env python3
import os
import sys
import re
import json
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlparse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Sources from A
SOURCES = [
    "https://github.com/gmtv4/rastaf/contents",
    "https://github.com/gratinomaster/1/raw/refs/heads/main/lista2.M3U",
    "https://github.com/iptv-org/iptv/raw/6b77242580c3b34d34f984265bfed2937708fce0/streams/us_moveonjoy.m3u",
    "https://github.com/strikeinthehouse/1/raw/refs/heads/main/lista_1.M3U",
    "https://github.com/otoxp/wepg/raw/df55b2ba14f8ec85bd198f85bd3c8cf35d3fa482/list/lista-globos-mitv.m3u",
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/REALITY.m3u",
    "https://github.com/iprtl/m3u/raw/b8507db8229defeda88512eaaf66bfe0e385e81c/Freetv.m3u",
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u",
    "https://github.com/punkrastafari/neta/raw/refs/heads/main/lista_final.m3u",
]

# B API sources
API_SOURCES = [
    "https://api.github.com/repos/gmtv4/rastaf/contents",
    "https://api.github.com/repos/gratinomaster/JCTV/contents",
    "https://api.github.com/repos/strikeinthehouse/YT-OK/contents",
    "https://api.github.com/repos/punkstarbr/STR-YT/contents",
]

# C scheduled - fetch now as requested
SCHEDULED = [
    "https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u",
    "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U",
    "https://github.com/punkstarbr/STR-YT/raw/main/lista1.M3U",
    "https://github.com/strikeinthehouse/M3UPT/raw/main/M3U/M3UPT.m3u",
]

# E additional
ADDITIONAL = [
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/REALITY.m3u",
    "https://github.com/iprtl/m3u/raw/b8507db8229defeda88512eaaf66bfe0e385e81c/Freetv.m3u",
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u",
    "https://github.com/punkrastafari/neta/raw/refs/heads/main/lista_final.m3u",
]

ALL_SOURCES = list(dict.fromkeys(SOURCES + API_SOURCES + SCHEDULED + ADDITIONAL))


def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            # try utf-8, fallback latin-1
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return data.decode("latin-1", errors="ignore")
    except Exception as e:
        print(f"ERRO ao buscar {url}: {e}", file=sys.stderr)
        return None


def is_m3u_path(name):
    return name.lower().endswith((".m3u", ".m3u8"))


def handle_github_contents(url, out_parts):
    txt = fetch_url(url)
    if not txt:
        return
    try:
        items = json.loads(txt)
    except Exception:
        # maybe it's a raw file
        if is_m3u_path(url):
            out_parts.append(txt)
        return
    if isinstance(items, dict):
        items = [items]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if is_m3u_path(name):
            dl = item.get("download_url") or item.get("raw_url") or item.get("html_url")
            if dl:
                t = fetch_url(dl)
                if t:
                    out_parts.append(t)
            continue
        # if directory, recurse? common in contents
        if item.get("type") == "dir" and item.get("url"):
            handle_github_contents(item["url"], out_parts)


def main():
    out_parts = []
    for url in ALL_SOURCES:
        p = urlparse(url)
        path = p.path.lower()
        if "/api.github.com/repos/" in url and "/contents" in url:
            handle_github_contents(url, out_parts)
            continue
        if "/contents" in url and "github.com" in url and "/api." not in url:
            # convert web contents to API? or try to parse
            # web contents page is HTML; but user gave /contents links as shown
            # try API form
            m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/contents(/.*)?", url)
            if m:
                owner, repo, sub = m.groups()
                api = f"https://api.github.com/repos/{owner}/{repo}/contents{sub or ''}"
                handle_github_contents(api, out_parts)
                continue
        # raw file or general m3u
        if is_m3u_path(url):
            t = fetch_url(url)
            if t:
                out_parts.append(t)
            continue
        # fallback
        t = fetch_url(url)
        if t:
            # if JSON, maybe contents
            try:
                j = json.loads(t)
                handle_github_contents(url, out_parts) if False else None  # no
            except Exception:
                pass
            if is_m3u_path(url) or "#EXTM3U" in t[:200]:
                out_parts.append(t)

    # also handle any direct raw m3u from sources list explicitly
    combined = "\n".join(out_parts)
    # write
    out_path = "/home/runner/work/1/1/lista1.M3U"
    with open(out_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(combined)
    print(f"Gravado {len(combined)} chars em {out_path}")


if __name__ == "__main__":
    main()
