#!/usr/bin/env python3
import os
import sys
import re
import json
import urllib.request
import urllib.error
from urllib.parse import quote, urlparse, urlsplit, urlunsplit

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# A. Fontes diretas
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

# B. Repositorios consultados pela API do GitHub
API_SOURCES = [
    "https://api.github.com/repos/gmtv4/rastaf/contents",
    "https://api.github.com/repos/gratinomaster/JCTV/contents",
    "https://api.github.com/repos/strikeinthehouse/YT-OK/contents",
    "https://api.github.com/repos/punkstarbr/STR-YT/contents",
]

# C. Fontes para atualizacao programada
SCHEDULED_M3U_SOURCES = [
    "https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u",
    "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U",
    "https://github.com/punkstarbr/STR-YT/raw/main/lista1.M3U",
    "https://github.com/strikeinthehouse/M3UPT/raw/main/M3U/M3UPT.m3u",
]

# E. Fontes adicionais para coleta de playlists
ADDITIONAL_M3U_SOURCES = [
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/REALITY.m3u",
    "https://github.com/iprtl/m3u/raw/b8507db8229defeda88512eaaf66bfe0e385e81c/Freetv.m3u",
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u",
    "https://github.com/punkrastafari/neta/raw/refs/heads/main/lista_final.m3u",
]

ALL_SOURCES = list(dict.fromkeys(SOURCES + API_SOURCES + SCHEDULED_M3U_SOURCES + ADDITIONAL_M3U_SOURCES))

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lista1.m3u")

EXT_RE = re.compile(r"^#EXTINF:.*?,\s*(.*)\s*$", re.IGNORECASE)
_seen_urls = set()
_stats = {"ok": 0, "fail": 0, "dup": 0}


def iri_to_uri(url):
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@")
    query = quote(parts.query, safe="=&%:@+,/?")
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch_url(url, timeout=60):
    url = iri_to_uri(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        return data.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"ERRO ao buscar {url}: {e}", file=sys.stderr)
        return None


def is_m3u_name(name):
    return name.lower().endswith((".m3u", ".m3u8"))


def strip_ref_prefix(rest):
    """Converte caminhos tipo refs/heads/main/a.m3u ou <sha>/a.m3u em a.m3u."""
    for prefix in ("refs/heads/", "refs/tags/"):
        if rest.startswith(prefix):
            segs = rest.split("/", 3)
            return segs[3] if len(segs) == 4 else ""
    segs = rest.split("/", 1)
    if len(segs) == 2:
        return segs[1]
    return ""


def parse_entries(text):
    """Retorna lista de blocos #EXTINF ... url valide."""
    entries = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.upper().startswith("#EXTINF"):
            j = i + 1
            url = None
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or nxt.startswith("#"):
                    if nxt.upper().startswith("#EXTINF"):
                        break
                    j += 1
                    continue
                url = nxt
                break
            if url:
                m = EXT_RE.match(line)
                name = m.group(1).strip() if m else ""
                entries.append((line, name, url))
                i = j + 1
                continue
        i += 1
    return entries


def collect_m3u_from_contents(api_url, out, depth=0, seen_api=None):
    if seen_api is None:
        seen_api = set()
    if api_url in seen_api or depth > 3:
        return False
    seen_api.add(api_url)
    txt = fetch_url(api_url)
    if not txt:
        return False
    try:
        items = json.loads(txt)
    except Exception:
        if is_m3u_name(api_url):
            for e in parse_entries(txt):
                out.append(e)
            return True
        return False
    if isinstance(items, dict):
        if items.get("type") == "file" and (
            items.get("download_url") or is_m3u_name(items.get("name", ""))
        ):
            dl = items.get("download_url") or items.get("raw_url")
            if dl:
                t = fetch_url(dl)
                if t:
                    for e in parse_entries(t):
                        out.append(e)
                    return True
            return False
        items = [items]
    found = False
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "") or ""
        if is_m3u_name(name):
            dl = item.get("download_url") or item.get("raw_url")
            if dl:
                t = fetch_url(dl)
                if t:
                    for e in parse_entries(t):
                        out.append(e)
                    found = True
        elif item.get("type") == "dir" and item.get("url"):
            if collect_m3u_from_contents(item["url"], out, depth + 1, seen_api):
                found = True
    return found


def collect_case_insensitive(owner, repo, rel, out):
    """Tenta encontrar o arquivo ignorando maiusculas/minusculas."""
    parent, _, fname = rel.rpartition("/")
    api = f"https://api.github.com/repos/{owner}/{repo}/contents"
    if parent:
        api += f"/{parent}"
    req_url = api
    for _ in range(3):
        txt = fetch_url(req_url)
        if not txt:
            return False
        try:
            items = json.loads(txt)
        except Exception:
            return False
        if isinstance(items, dict):
            items = [items]
        hit = next(
            (
                i
                for i in items
                if isinstance(i, dict)
                and (i.get("name", "") or "").lower() == fname.lower()
            ),
            None,
        )
        if hit is None:
            return False
        if hit.get("type") == "dir":
            req_url = hit.get("url")
            fname = ""
            continue
        dl = hit.get("download_url") or hit.get("raw_url")
        if not dl:
            return False
        t = fetch_url(dl)
        if not t:
            return False
        for e in parse_entries(t):
            out.append(e)
        return True
    return False


def handle_source(url, out):
    p = urlparse(url)
    host = p.netloc.lower()

    # API do GitHub (diretorio)
    if host == "api.github.com" and "/contents" in p.path:
        collect_m3u_from_contents(url, out)
        return

    # Pagina web /contents -> converte para API
    if host == "github.com" and "/contents" in p.path:
        m = re.match(r"^/([^/]+)/([^/]+)(/contents.*)?$", p.path)
        if m:
            owner, repo, sub = m.groups()
            sub = "" if not sub or sub.strip("/") == "contents" else sub
            api = f"https://api.github.com/repos/{owner}/{repo}/contents{sub}"
            collect_m3u_from_contents(api, out)
            return

    # Arquivo direto: se der 404, tenta localizar via API do repositorio
    txt = fetch_url(url)
    if not txt:
        m = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/raw/(.+)$", url)
        if m:
            owner, repo, rest = m.groups()
            rel = strip_ref_prefix(rest)
            if rel:
                api = f"https://api.github.com/repos/{owner}/{repo}/contents/{rel}"
                if not collect_m3u_from_contents(api, out):
                    collect_case_insensitive(owner, repo, rel, out)
        return
    if "#EXTM3U" in txt[:500] or is_m3u_name(p.path):
        for e in parse_entries(txt):
            out.append(e)
        return
    # Resposta que ainda pode ser JSON de conteudo
    try:
        json.loads(txt)
        collect_m3u_from_contents(url, out)
    except Exception:
        pass


def main():
    entries = []
    for url in ALL_SOURCES:
        before = len(entries)
        handle_source(url, entries)
        got = len(entries) - before
        status = "ok" if got else "VAZIO"
        print(f"[{status}] {url} -> {got} entradas")

    out_lines = ["#EXTM3U"]
    for extinf, name, url in entries:
        key = url.strip()
        if key in _seen_urls:
            _stats["dup"] += 1
            continue
        _seen_urls.add(key)
        out_lines.append(extinf)
        out_lines.append(key)
        _stats["ok"] += 1

    # Apaga o conteudo anterior e grava os canais novos
    with open(OUT_PATH, "w", encoding="utf-8", errors="ignore") as f:
        f.write("\n".join(out_lines) + "\n")

    print(
        f"Gravado {len(out_lines)} linhas ({_stats['ok']} canais, "
        f"{_stats['dup']} duplicados removidos) em {OUT_PATH}"
    )


if __name__ == "__main__":
    main()
