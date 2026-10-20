import json
import re
from datetime import datetime, time
from urllib.parse import quote

import pytz
import requests

TIMEZONE = pytz.timezone("America/Sao_Paulo")
OUTPUT_FILE = "lista1.M3U"
REQUEST_TIMEOUT = 30
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

M3U_SOURCES = [
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


def fetch_text(url):
    try:
        response = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.text
        print(f"  Erro HTTP {response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"  Falha ao acessar {url}: {e}")
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
        if url:
            name = line.split(",")[-1].strip()
            entries.append({"extinf": line, "extras": extras, "url": url, "name": name})
        i = j
    return entries


def collect_from_url(url):
    print(f"Processando: {url}")
    text = fetch_text(url)
    if text is None:
        return [], []

    epg_urls = []
    if url.lower().endswith((".m3u", ".m3u8")) or "#EXTM3U" in text[:200]:
        print("  Arquivo M3U direto")
        header = text.splitlines()[0] if text.splitlines() else ""
        epg_urls.extend(extract_epg_urls(header))
        return parse_m3u(text), epg_urls

    try:
        contents = json.loads(text)
    except ValueError:
        print("  Conteudo nao reconhecido, ignorando")
        return [], []

    print(f"  Diretorio GitHub com {len(contents)} itens")
    entries = []
    for item in contents:
        name = item.get("name", "")
        if not name.lower().endswith((".m3u", ".m3u8")):
            continue
        download_url = item.get("download_url")
        if not download_url:
            continue
        print(f"  Baixando: {name}")
        m3u_text = fetch_text(download_url)
        if m3u_text is None:
            continue
        first = m3u_text.splitlines()[0] if m3u_text.splitlines() else ""
        epg_urls.extend(extract_epg_urls(first))
        entries.extend(parse_m3u(m3u_text))
    return entries, epg_urls


def in_schedule(start, end):
    now = datetime.now(TIMEZONE).time()
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end


def collect_vod():
    entries = []
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
                files = meta_response.json().get("files", [])
            except (requests.exceptions.RequestException, ValueError):
                continue

            video_file = next(
                (f for f in files if f.get("name", "").lower().endswith((".mp4", ".mpeg4", ".webm", ".ogv"))),
                None,
            )
            if not video_file:
                continue

            title = doc.get("title") or identifier
            thumbnail = f"https://archive.org/services/img/{identifier}"
            play_url = f"https://archive.org/download/{identifier}/{quote(video_file['name'])}"
            entries.append({
                "extinf": f'#EXTINF:-1 group-title="VOD" tvg-logo="{thumbnail}",{title}',
                "extras": [],
                "url": play_url,
                "name": title,
            })
            print(f"  VOD encontrado: {title}")
    return entries


def main():
    all_entries = []
    epg_urls = []
    seen_sources = set()

    source_groups = [(M3U_SOURCES, "fontes fixas"), (ADDITIONAL_M3U_SOURCES, "fontes adicionais")]
    for sources, label in source_groups:
        print(f"\n=== {label} ===")
        for url in sources:
            if url in seen_sources:
                print(f"Ja processada, ignorando duplicata: {url}")
                continue
            seen_sources.add(url)
            entries, found_epg = collect_from_url(url)
            all_entries.extend(entries)
            epg_urls.extend(found_epg)

    print("\n=== API do GitHub ===")
    for api_url in GITHUB_API_SOURCES:
        if api_url in seen_sources:
            continue
        seen_sources.add(api_url)
        print(f"Processando API: {api_url}")
        text = fetch_text(api_url)
        if text is None:
            continue
        try:
            contents = json.loads(text)
        except ValueError:
            print("  Resposta nao e JSON, ignorando")
            continue
        for item in contents:
            name = item.get("name", "")
            if not name.lower().endswith((".m3u", ".m3u8")):
                continue
            download_url = item.get("download_url")
            if not download_url or download_url in seen_sources:
                continue
            seen_sources.add(download_url)
            print(f"  Baixando: {name}")
            m3u_text = fetch_text(download_url)
            if m3u_text is None:
                continue
            first = m3u_text.splitlines()[0] if m3u_text.splitlines() else ""
            epg_urls.extend(extract_epg_urls(first))
            all_entries.extend(parse_m3u(m3u_text))

    print("\n=== Fontes programadas (America/Sao_Paulo) ===")
    scheduled_urls = set()
    for source in SCHEDULED_M3U_SOURCES:
        if source["url"] in scheduled_urls:
            continue
        if not in_schedule(source["start"], source["end"]):
            print(f"Fora do horario ({source['start'].strftime('%H:%M')}-{source['end'].strftime('%H:%M')}): {source['url']}")
            continue
        scheduled_urls.add(source["url"])
        entries, found_epg = collect_from_url(source["url"])
        all_entries.extend(entries)
        epg_urls.extend(found_epg)

    print("\n=== VOD Internet Archive ===")
    all_entries.extend(collect_vod())

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

    print(f"\n{OUTPUT_FILE} salvo com {len(deduped)} canais ({len(all_entries)} antes da remocao de duplicados)")
    if unique_epg:
        print("EPG preservado:")
        for epg_url in unique_epg:
            print(f"  - {epg_url}")


if __name__ == "__main__":
    main()
