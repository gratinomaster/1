import json
import os
import re
import time
from urllib.parse import quote
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def pick_video(files):
    keys = []
    for f in files:
        name = f.get("name", "")
        fmt = (f.get("format") or "").lower()
        ext = os.path.splitext(name)[1].lower()
        if fmt.startswith("mpeg4") or ext in (".mp4", ".m4v"):
            score = 2
            if "512kb" in name:
                score += 10
            elif "64kb" in name or "160kb" in name or "256kb" in name:
                score += 5
            keys.append((score, -len(name), name, "mp4"))
        elif fmt.startswith("ogg video") or ext in (".ogv", ".webm"):
            keys.append((1, -len(name), name, "video"))
        elif ext in (".mpg", ".mpeg", ".mpg4"):
            keys.append((0, -len(name), name, "video"))
    if not keys:
        return None
    keys.sort(reverse=True)
    return keys[0][2]


def main():
    with open("lota_items.json", encoding="utf-8") as f:
        docs = json.load(f)

    entries = []
    missing = []
    for i, doc in enumerate(docs):
        if len(entries) >= 50:
            break
        ident = doc["identifier"]
        url = f"https://archive.org/metadata/{ident}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                missing.append((ident, f"status {r.status_code}"))
                continue
            meta = r.json()
            files = meta.get("files", [])
            filename = pick_video(files)
            if not filename:
                missing.append((ident, "no video file"))
                continue
            enc = quote(filename, safe="")
            media_url = f"https://archive.org/download/{ident}/{enc}"
            thumb = f"https://archive.org/download/{ident}/__ia_thumb.jpg"
            title = doc.get("title") or ident
            entries.append({
                "identifier": ident,
                "title": title,
                "date": doc.get("date", ""),
                "creator": doc.get("creator", ""),
                "url": media_url,
                "thumbnail": thumb,
            })
        except Exception as e:
            missing.append((ident, str(e)))
        time.sleep(0.4)

    with open("lota_media.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"entradas resolvidas: {len(entries)}")
    print(f"sem vídeo: {len(missing)}")
    for ident, reason in missing[:10]:
        print("  X", ident, "-", reason)

    with open("LOTA.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in entries:
            f.write(f'#EXTINF:-1 tvg-logo="{e["thumbnail"]}" group-title="Archive.org Documentary",{e["title"]}\n')
            f.write(f'{e["url"]}\n')
    print("LOTA.m3u gerado")


if __name__ == "__main__":
    main()