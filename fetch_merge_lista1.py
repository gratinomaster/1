#!/usr/bin/env python3
import os
import re
import json
import time
import base64
from urllib.parse import urlparse, unquote, parse_qs, quote

import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Sources
A_DIRECT = [
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

GITHUB_API_SOURCES = [
    "https://api.github.com/repos/gmtv4/rastaf/contents",
    "https://api.github.com/repos/gratinomaster/JCTV/contents",
    "https://api.github.com/repos/strikeinthehouse/YT-OK/contents",
    "https://api.github.com/repos/punkstarbr/STR-YT/contents",
]

SCHEDULED_M3U_SOURCES = [
    "https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u",
    "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U",
    "https://github.com/punkstarbr/STR-YT/raw/main/lista1.M3U",
    "https://github.com/strikeinthehouse/M3UPT/raw/main/M3U/M3UPT.m3u",
]

ADDITIONAL_M3U_SOURCES = [
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/REALITY.m3u",
    "https://github.com/iprtl/m3u/raw/b8507db8229defeda88512eaaf66bfe0e385e81c/Freetv.m3u",
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u",
    "https://github.com/punkrastafari/neta/raw/refs/heads/main/lista_final.m3u",
]

VOD_SOURCES = [
    "https://archive.org/details/television?query=cbs&sort=date&tab=collection",
]

VIDEO_EXTS = ('.mp4', '.m4v', '.webm', '.mkv', '.ogv', '.avi', '.mov')
VIDEO_FORMATS = {
    'mpeg4', 'h.264', 'h.264 ia', 'matroska', 'ogg video', 'webm',
    '512kb mpeg4', 'mpeg2', 'mpeg1', 'divx', 'quicktime', 'windows media',
}

def is_direct_file_url(url):
    url_lower = url.lower()
    if url_lower.endswith(('.m3u', '.m3u8')):
        return True
    if '/raw/' in url_lower:
        return True
    return False

def fetch_url(url):
    last_error = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    print(f"[ERR] fetch {url}: {last_error}")
    return None

def normalize_contents_url(url):
    match = re.match(r'^https?://github\.com/([^/]+)/([^/]+)/contents(?:/(.*))?$', url)
    if match:
        owner, repo, path = match.group(1), match.group(2), match.group(3)
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
        if path:
            api_url += '/' + path
        return api_url
    return url

def fetch_github_contents_dir(api_url):
    api_url = normalize_contents_url(api_url)
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            # might be a file
            if data.get('download_url'):
                content = fetch_url(data['download_url'])
                return [(data.get('name', ''), content)]
            if data.get('content') and data.get('encoding') == 'base64':
                try:
                    decoded = base64.b64decode(data['content']).decode('utf-8', errors='replace')
                    return [(data.get('name', ''), decoded)]
                except:
                    pass
            return []
        results = []
        if isinstance(data, list):
            for item in data:
                name = item.get('name', '')
                if name.lower().endswith(('.m3u', '.m3u8')):
                    dl = item.get('download_url')
                    if dl:
                        content = fetch_url(dl)
                        if content:
                            results.append((name, content))
                    else:
                        if item.get('url'):
                            c2 = fetch_github_contents_dir(item['url'])
                            results.extend(c2)
        return results
    except Exception as e:
        print(f"[ERR] api {api_url}: {e}")
        return []

def extract_m3u_entries(text):
    if not text:
        return []
    entries = []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF'):
            extinf = line
            # find next non-empty non-comment? or next url line
            j = i + 1
            while j < len(lines):
                l2 = lines[j].strip()
                if not l2:
                    j += 1
                    continue
                if l2.startswith('#EXTINF'):
                    # Next entry started without a URL for this one.
                    break
                if l2.startswith('#'):
                    # skip other directives
                    j += 1
                    continue
                # Some playlists prefix the URL with "+"; normalize it.
                l2 = l2.lstrip('+').strip()
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', l2):
                    # Not a usable stream URL; skip this entry.
                    break
                entries.append((extinf, l2))
                i = j
                break
            else:
                pass
        i += 1
    return entries

def fetch_archive_vod(source, max_items=80, max_videos=60):
    """Pesquisa itens de vídeo no Internet Archive e retorna apenas os reproduzíveis."""
    parsed = urlparse(source)
    collection = ''
    if '/details/' in parsed.path:
        collection = parsed.path.split('/details/', 1)[1].split('/')[0]
    query = parse_qs(parsed.query).get('query', [''])[0]

    search = f'collection:{collection}' if collection else ''
    if query:
        search = (search + ' AND ' + query).strip() if search else query
    if not search:
        return []

    api_url = 'https://archive.org/advancedsearch.php'
    params = {
        'q': search,
        'fl[]': ['identifier', 'title'],
        'rows': str(max_items),
        'page': '1',
        'output': 'json',
    }
    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        docs = resp.json().get('response', {}).get('docs', [])
    except Exception as e:
        print(f"[ERR] archive search {source}: {e}")
        return []

    results = []
    for doc in docs:
        if len(results) >= max_videos:
            break
        ident = doc.get('identifier')
        if not ident:
            continue
        try:
            meta_resp = requests.get(f'https://archive.org/metadata/{ident}', headers=HEADERS, timeout=60)
            meta_resp.raise_for_status()
            meta = meta_resp.json()
        except Exception as e:
            print(f"[ERR] archive metadata {ident}: {e}")
            continue

        title = meta.get('metadata', {}).get('title') or doc.get('title') or ident
        logo = f'https://archive.org/services/img/{ident}'
        chosen = None
        for f in meta.get('files', []):
            name = f.get('name') or ''
            lower = name.lower()
            fmt = (f.get('format') or '').lower()
            if fmt in VIDEO_FORMATS or lower.endswith(VIDEO_EXTS):
                if lower.endswith(('.thumbs', '. torrent', '.torrent', '.xml', '.txt')):
                    continue
                chosen = name
                break
        if not chosen:
            continue

        video_url = f'https://archive.org/download/{ident}/{quote(chosen)}'
        safe_title = str(title).replace('"', "'").replace('\n', ' ').strip()
        extinf = f'#EXTINF:-1 group-title="VOD" tvg-logo="{logo}",{safe_title}'
        results.append((extinf, video_url))
    return results


def main():
    all_entries = []
    seen = set()

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lista1.M3U')
    header = '#EXTM3U'
    if os.path.exists(out_path):
        try:
            with open(out_path, 'r', encoding='utf-8', errors='replace') as f:
                first = f.readline().strip()
            if first.startswith('#EXTM3U'):
                header = first
        except Exception:
            pass
    
    # Collect from all sources as requested
    sources_to_fetch = []
    # A
    for s in A_DIRECT:
        sources_to_fetch.append(('direct_or_contents', s))
    # B
    for s in GITHUB_API_SOURCES:
        sources_to_fetch.append(('api_contents', s))
    # C
    for s in SCHEDULED_M3U_SOURCES:
        sources_to_fetch.append(('direct_or_contents', s))
    # E
    for s in ADDITIONAL_M3U_SOURCES:
        sources_to_fetch.append(('direct_or_contents', s))
    
    # Also deduplicate sources
    uniq_sources = []
    seen_src = set()
    for t, s in sources_to_fetch:
        if s in seen_src:
            continue
        seen_src.add(s)
        uniq_sources.append((t, s))
    
    for stype, url in uniq_sources:
        print(f"[FETCH] {url}")
        if stype == 'api_contents':
            # try as api contents
            if '/contents' in url and not url.startswith('https://raw.githubusercontent.com'):
                files = fetch_github_contents_dir(url)
                for name, content in files:
                    ents = extract_m3u_entries(content)
                    for extinf, murl in ents:
                        key = murl.strip()
                        if key in seen:
                            continue
                        seen.add(key)
                        all_entries.append((extinf, murl))
                continue
        # direct
        if is_direct_file_url(url) or '/raw/' in url.lower():
            content = fetch_url(url)
            if content:
                ents = extract_m3u_entries(content)
                for extinf, murl in ents:
                    key = murl.strip()
                    if key in seen:
                        continue
                    seen.add(key)
                    all_entries.append((extinf, murl))
                continue
        # else try as contents
        if '/contents' in url:
            files = fetch_github_contents_dir(url)
            for name, content in files:
                ents = extract_m3u_entries(content)
                for extinf, murl in ents:
                    key = murl.strip()
                    if key in seen:
                        continue
                    seen.add(key)
                    all_entries.append((extinf, murl))
            continue
        # fallback
        content = fetch_url(url)
        if content:
            ents = extract_m3u_entries(content)
            for extinf, murl in ents:
                key = murl.strip()
                if key in seen:
                    continue
                seen.add(key)
                all_entries.append((extinf, murl))
    
    # D - VOD do Internet Archive
    for s in VOD_SOURCES:
        print(f"[VOD] {s}")
        for extinf, murl in fetch_archive_vod(s):
            key = murl.strip()
            if key in seen:
                continue
            seen.add(key)
            all_entries.append((extinf, murl))

    # Write to lista1.M3U overwriting
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(header + '\n')
        for extinf, murl in all_entries:
            f.write(extinf + '\n')
            f.write(murl.strip() + '\n')
    
    print(f"[DONE] Wrote {len(all_entries)} entries to {out_path}")

if __name__ == '__main__':
    main()
