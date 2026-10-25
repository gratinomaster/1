import gzip
import hashlib
import json
import os
import re
from datetime import datetime, time
from time import sleep
from urllib.parse import quote

import pytz
import requests

TIMEZONE = pytz.timezone("America/Sao_Paulo")
OUTPUT_FILE = "lista1.M3U"
CACHE_DIR = ".m3u_cache"
MANIFEST_FILE = os.path.join(CACHE_DIR, "manifest.json")
REQUEST_TIMEOUT = 30
CONNECT_TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

M3U_SOURCES = [
    "https://github.com/gmtv4/rastaf/contents",
    "https://github.com/gratinomaster/1/raw/refs/heads/main/lista2.M3U",
    "https://github.com/iptv-org/iptv/raw/6b77242580c3b34d34f984265bfed2937708fce0/streams/us_moveonjoy.m3u",
    "https://github.com/strikeinthehouse/1/raw/refs/heads/main/lista_1.M3U",
    "https://github.com/toxp/wepg/raw/df55b2ba14f8ec85bd198f85bd3c8cf35d3fa482/list/lista-globos-mitv.m3u",
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
    {"url": "https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u", "start": time(17, 30), "end": time(23, 0)},
    {"url": "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U", "start": time(11, 30), "end": time(13, 30)},
    {"url": "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U", "start": time(19, 0), "end": time(19, 45)},
    {"url": "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U", "start": time(17, 30), "end": time(20, 0)},
    {"url": "https://github.com/punkstarbr/STR-YT/raw/main/lista1.M3U", "start": time(6, 0), "end": time(23, 59)},
    {"url": "https://github.com/strikeinthehouse/M3UPT/raw/main/M3U/M3UPT.m3u", "start": time(6, 0), "end": time(23, 59)},
]

VOD_SOURCES = [
    "https://archive.org/details/television?query=cbs&sort=date&tab=collection",
]

ADDITIONAL_M3U_SOURCES = [
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/REALITY.m3u",
    "https://github.com/iprtl/m3u/raw/b8507db8229defeda88512eaaf66bfe0e385e81c/Freetv.m3u",
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u",
    "https://github.com/punkrastafari/neta/raw/refs/heads/main/lista_final.m3u",
]

SOURCE_FALLBACKS = {
    "https://github.com/gmtv4/rastaf/contents": [
        "https://api.github.com/repos/gmtv4/rastaf/contents",
    ],
    "https://github.com/strikeinthehouse/1/raw/refs/heads/main/lista_1.M3U": [
        "https://raw.githubusercontent.com/gratinomaster/JCTV/main/lista1.m3u",
        "https://raw.githubusercontent.com/Mahiroooh270/canaisinternacionaiss/main/iptvinternacional",
    ],
    "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U": [
        "https://github.com/gratinomaster/1/raw/main/lista2.M3U",
    ],
    "https://github.com/strikeinthehouse/M3UPT/raw/main/M3U/M3UPT.m3u": [
        "https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u",
    ],
    "https://github.com/punkstarbr/STR-YT/raw/main/lista1.M3U": [
        "https://github.com/punkstarbr/STR-YT/raw/main/lista1.m3u",
    ],
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/lista1.M3U": [
        "https://raw.githubusercontent.com/punkstarbr/STR-YT/main/lista1.m3u",
    ],
    "https://github.com/toxp/wepg/raw/df55b2ba14f8ec85bd198f85bd3c8cf35d3fa482/list/lista-globos-mitv.m3u": [
        "https://raw.githubusercontent.com/25011966V/iptv/master/Teste",
    ],
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u": [
        "https://web.archive.org/web/20260208044525if_/https://raw.githubusercontent.com/ipstreet312/freeiptv/master/all.m3u",
        "https://raw.githubusercontent.com/Fraewin/iptv/main/playlist.m3u",
    ],
    "https://api.github.com/repos/strikeinthehouse/YT-OK/contents": [
        "https://api.github.com/repos/punkstarbr/STR-YT/contents",
    ],
}

GITHUB_CONTENTS_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/contents/?$", re.IGNORECASE
)
GITHUB_RAW_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/raw/(?P<refs>refs/heads/)?(?P<branch>[^/]+)/(?P<path>.+)$",
    re.IGNORECASE,
)
VIDEO_EXTENSIONS = (".mp4", ".m4v", ".mpeg4", ".webm", ".ogv", ".mov")
PLACEHOLDER_URLS = {
    "http://blank",
    "https://blank",
    "http://section",
    "https://section",
    "blank",
    "section",
}
MANIFEST = {}


def normalize_stream_url(url):
    if not url:
        return None
    cleaned = url.strip()
    while cleaned.startswith("+"):
        cleaned = cleaned[1:].strip()
    return cleaned


def is_stream_url(url):
    if not url or "://" not in url:
        return False
    if url.strip().lower() in PLACEHOLDER_URLS:
        return False
    if url.lower().startswith("error"):
        return False
    return True


def fetch_text(url, retries=2):
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                allow_redirects=True,
                timeout=(CONNECT_TIMEOUT, REQUEST_TIMEOUT),
            )
            if response.status_code == 200:
                return response.text
            if response.status_code in (429, 502, 503) and attempt < retries:
                print(f"  HTTP {response.status_code}, nova tentativa em 10s")
                sleep(10)
                continue
            print(f"  Erro HTTP {response.status_code}: {url}")
        except requests.exceptions.RequestException as e:
            print(f"  Falha ao acessar {url}: {e}")
            if attempt < retries:
                sleep(10)
                continue
    return None


def extract_epg_urls(line):
    urls = []
    for value in re.findall(r'(?:url-tvg|tvg-url|x-tvg-url)=["\']([^"\']+)["\']', line, flags=re.IGNORECASE):
        for part in re.split(r'[,|]', value):
            part = part.strip()
            if part.startswith("http") and part not in urls:
                urls.append(part)
    return urls


def parse_m3u(text):
    entries = []
    lines = [line.strip() for line in text.splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("#EXTINF"):
            i += 1
            continue
        extras = []
        url = None
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt:
                j += 1
                continue
            if nxt.startswith("#"):
                if nxt.startswith("#EXTM3U") or nxt.startswith("#EXTINF"):
                    break
                extras.append(nxt)
                j += 1
            else:
                url = nxt
                j += 1
                break
        if url and not is_stream_url(url):
            url = None
        url = normalize_stream_url(url)
        if url:
            if "," in line:
                name = line.split(",")[-1].strip()
            else:
                match = re.search(r'tvg-name="([^"]*)"', line)
                name = match.group(1).strip() if match else line.strip()
            entries.append({"extinf": line, "extras": extras, "url": url, "name": name})
        i = j
    return entries


def normalize_source_url(url):
    match = GITHUB_CONTENTS_PATTERN.match(url)
    if match:
        return f"https://api.github.com/repos/{match.group('owner')}/{match.group('repo')}/contents"
    return url


def raw_github_equivalent(url):
    match = GITHUB_RAW_PATTERN.match(url)
    if not match:
        return None
    owner = match.group("owner")
    repo = match.group("repo")
    branch = match.group("branch")
    path = match.group("path")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"


def cache_path(url):
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{digest}.m3u.gz")


def render_playlist(entries, epg_urls):
    lines = ["#EXTM3U"]
    if epg_urls:
        attrs = " ".join(f'url-tvg="{epg_url}"' for epg_url in epg_urls)
        lines[0] = f"#EXTM3U {attrs}"
    for entry in entries:
        lines.append(entry["extinf"])
        lines.extend(entry["extras"])
        lines.append(entry["url"])
    return "\n".join(lines) + "\n"


def load_cache(url):
    path = cache_path(url)
    if not os.path.exists(path):
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            text = f.read()
    except (OSError, EOFError, gzip.BadGzipFile) as e:
        print(f"  Falha ao ler cache: {e}")
        return None
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return parse_m3u(text), extract_epg_urls(first_line)


def save_cache(url, entries, epg_urls):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with gzip.open(cache_path(url), "wt", encoding="utf-8") as f:
            f.write(render_playlist(entries, epg_urls))
        MANIFEST[url] = {
            "updated_at": datetime.now(TIMEZONE).isoformat(timespec="seconds"),
            "channels": len(entries),
        }
    except OSError as e:
        print(f"  Falha ao gravar cache: {e}")


def save_manifest():
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(MANIFEST, f, indent=2, ensure_ascii=False, sort_keys=True)
    except OSError as e:
        print(f"Falha ao gravar manifesto: {e}")


def load_manifest():
    if not os.path.exists(MANIFEST_FILE):
        return
    try:
        with open(MANIFEST_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            MANIFEST.update(data)
    except (OSError, ValueError) as e:
        print(f"Falha ao ler manifesto: {e}")


def parse_payload(url, text, downloaded):
    epg_urls = []
    lines = text.splitlines()
    first_line = lines[0] if lines else ""

    if url.lower().endswith((".m3u", ".m3u8")) or "#EXTM3U" in text[:200]:
        print("  Arquivo M3U direto")
        epg_urls.extend(extract_epg_urls(first_line))
        return parse_m3u(text), epg_urls

    try:
        contents = json.loads(text)
    except ValueError:
        print("  Conteudo nao reconhecido, ignorando")
        return [], []

    if not isinstance(contents, list):
        print("  Resposta JSON invalida, ignorando")
        return [], []

    print(f"  Diretorio GitHub com {len(contents)} itens")
    entries = []
    for item in contents:
        name = item.get("name", "")
        if not name.lower().endswith((".m3u", ".m3u8")):
            continue
        download_url = item.get("download_url")
        if not download_url or download_url in downloaded:
            continue
        downloaded.add(download_url)
        print(f"  Baixando: {name}")
        m3u_text = fetch_text(download_url)
        if m3u_text is None:
            continue
        sub_lines = m3u_text.splitlines()
        epg_urls.extend(extract_epg_urls(sub_lines[0] if sub_lines else ""))
        entries.extend(parse_m3u(m3u_text))
    return entries, epg_urls


def source_candidates(url):
    candidates = []
    target = normalize_source_url(url)
    if target != url:
        print(f"  Convertido para API: {target}")
    candidates.append(target)
    raw_equivalent = raw_github_equivalent(url)
    if raw_equivalent and raw_equivalent not in candidates:
        candidates.append(raw_equivalent)
    for fallback in SOURCE_FALLBACKS.get(url, []):
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def fetch_source(url, downloaded):
    empty_result = None
    for candidate in source_candidates(url):
        if candidate != normalize_source_url(url):
            print(f"  Tentando alternativa: {candidate}")
        text = fetch_text(candidate)
        if text is None:
            continue
        entries, epg_urls = parse_payload(candidate, text, downloaded)
        if entries:
            return entries, epg_urls, True
        if empty_result is None:
            empty_result = (entries, epg_urls)
    if empty_result is not None:
        return empty_result[0], empty_result[1], True
    return [], [], False


def collect_source(url, downloaded, allow_network=True):
    if allow_network:
        entries, epg_urls, ok = fetch_source(url, downloaded)
        if ok:
            save_cache(url, entries, epg_urls)
            return entries, epg_urls
        print("  Fonte indisponivel, preservando dados anteriores")
    else:
        print("  Fora do horario, sem atualizar")
    cached = load_cache(url)
    if cached is None:
        if not allow_network:
            print("  Sem cache anterior, coletando uma unica vez")
            entries, epg_urls, ok = fetch_source(url, downloaded)
            if ok:
                save_cache(url, entries, epg_urls)
                return entries, epg_urls
        print("  Sem dados preservados")
        return [], []
    print(f"  Dados preservados do cache: {len(cached[0])} canais")
    return cached[0], cached[1]


def in_schedule(start, end):
    now = datetime.now(TIMEZONE).time()
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end


def collect_vod(downloaded):
    entries = []
    epg_urls = []
    print("Processando VOD do Internet Archive")
    for details_url in VOD_SOURCES:
        match = re.search(r"query=([^&]+)", details_url)
        query_term = match.group(1) if match else "cbs"
        params = [
            ("q", f"collection:television AND {query_term}"),
            ("fl[]", "identifier"),
            ("fl[]", "title"),
            ("rows", "25"),
            ("page", "1"),
            ("output", "json"),
            ("sort[]", "date desc"),
        ]
        try:
            response = requests.get(
                "https://archive.org/advancedsearch.php",
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            docs = response.json().get("response", {}).get("docs", [])
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"  Falha na busca do Archive: {e}")
            continue

        for doc in docs:
            identifier = doc.get("identifier")
            if not identifier:
                continue
            try:
                meta_response = requests.get(
                    f"https://archive.org/metadata/{identifier}",
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )
                meta_response.raise_for_status()
                meta = meta_response.json()
            except (requests.exceptions.RequestException, ValueError):
                continue

            files = meta.get("files", [])
            video_file = None
            for candidate in files:
                name = candidate.get("name", "")
                if not name.lower().endswith(VIDEO_EXTENSIONS):
                    continue
                if candidate.get("private") or candidate.get("private_original"):
                    continue
                if candidate.get("source") == "derivative":
                    continue
                video_file = candidate
                break
            if not video_file:
                continue

            title = doc.get("title") or meta.get("metadata", {}).get("title") or identifier
            thumbnail = f"https://archive.org/services/img/{identifier}"
            play_url = f"https://archive.org/download/{identifier}/{quote(video_file['name'])}"
            entries.append({
                "extinf": f'#EXTINF:-1 group-title="VOD" tvg-logo="{thumbnail}",{title}',
                "extras": [],
                "url": play_url,
                "name": title,
            })
            print(f"  VOD encontrado: {title}")
    return entries, epg_urls


def main():
    load_manifest()
    all_entries = []
    epg_urls = []
    seen_sources = set()
    downloaded = set()

    source_groups = [(M3U_SOURCES, "fontes fixas"), (ADDITIONAL_M3U_SOURCES, "fontes adicionais")]
    for sources, label in source_groups:
        print(f"\n=== {label} ===")
        for url in sources:
            if url in seen_sources:
                print(f"Ja processada, ignorando duplicata: {url}")
                continue
            seen_sources.add(url)
            print(f"Processando: {url}")
            entries, found_epg = collect_source(url, downloaded)
            all_entries.extend(entries)
            epg_urls.extend(found_epg)

    print("\n=== API do GitHub ===")
    for api_url in GITHUB_API_SOURCES:
        if api_url in seen_sources:
            continue
        seen_sources.add(api_url)
        print(f"Processando API: {api_url}")
        entries, found_epg = collect_source(api_url, downloaded)
        all_entries.extend(entries)
        epg_urls.extend(found_epg)

    print("\n=== Fontes adicionais (E) ===")
    for add_url in ADDITIONAL_M3U_SOURCES:
        if add_url in seen_sources:
            continue
        seen_sources.add(add_url)
        print(f"Processando: {add_url}")
        entries, found_epg = collect_source(add_url, downloaded)
        all_entries.extend(entries)
        epg_urls.extend(found_epg)

    print("\n=== Fontes programadas (America/Sao_Paulo) ===")
    scheduled_urls = set()
    for source in SCHEDULED_M3U_SOURCES:
        if source["url"] in scheduled_urls:
            continue
        window = f"{source['start'].strftime('%H:%M')}-{source['end'].strftime('%H:%M')}"
        if not in_schedule(source["start"], source["end"]):
            print(f"Fora do horario ({window}): {source['url']}")
            entries, found_epg = collect_source(source["url"], downloaded, allow_network=False)
            all_entries.extend(entries)
            epg_urls.extend(found_epg)
            continue
        scheduled_urls.add(source["url"])
        print(f"Processando ({window}): {source['url']}")
        entries, found_epg = collect_source(source["url"], downloaded)
        all_entries.extend(entries)
        epg_urls.extend(found_epg)

    print("\n=== VOD Internet Archive ===")
    vod_entries, vod_epg = collect_vod(downloaded)
    if vod_entries:
        save_cache(VOD_SOURCES[0], vod_entries, vod_epg)
        all_entries.extend(vod_entries)
        epg_urls.extend(vod_epg)
    else:
        cached = load_cache(VOD_SOURCES[0])
        if cached:
            print(f"  VOD preservado do cache: {len(cached[0])} itens")
            all_entries.extend(cached[0])
            epg_urls.extend(cached[1])

    deduped = []
    seen_channels = set()
    for entry in all_entries:
        key = (entry["name"].lower(), entry["url"])
        if key in seen_channels:
            continue
        seen_channels.add(key)
        deduped.append(entry)

    unique_epg = []
    for epg_url in epg_urls:
        if epg_url not in unique_epg:
            unique_epg.append(epg_url)

    header = "#EXTM3U"
    if unique_epg:
        attrs = " ".join(f'url-tvg="{url}"' for url in unique_epg)
        header = f"#EXTM3U {attrs}"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for entry in deduped:
            f.write(entry["extinf"] + "\n")
            for extra in entry["extras"]:
                f.write(extra + "\n")
            f.write(entry["url"] + "\n")

    save_manifest()

    print(f"\n{OUTPUT_FILE} salvo com {len(deduped)} canais ({len(all_entries)} antes da remocao de duplicados)")
    if unique_epg:
        print(f"EPG preservado: {len(unique_epg)} URLs")


if __name__ == "__main__":
    main()
