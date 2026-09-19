import subprocess
import re
import sys


def parse_m3u(path):
    entries = []
    url = None
    extinf = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#EXTINF"):
                m = re.search(r',(.*)$', line)
                extinf = m.group(1) if m else "?"
            elif line and not line.startswith("#"):
                entries.append({"url": line, "title": extinf})
    return entries


def test_url(url, timeout=60):
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             "-t", "4",
             "-i", url, "-f", "null", "-"],
            capture_output=True, text=True, timeout=timeout,
        )
        err = r.stderr.strip().replace("\n", " | ")[:180]
        return r.returncode == 0, err
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "LOTA.m3u"
    entries = parse_m3u(path)
    print(f"total entradas: {len(entries)}")
    ok = 0
    fail = 0
    for i, e in enumerate(entries):
        good, detail = test_url(e["url"])
        status = "OK " if good else "FAIL"
        if good:
            ok += 1
        else:
            fail += 1
        print(f"[{i+1:3d}] {status} {e['title'][:60]}")
        if not good:
            print(f"       {detail}")
    print(f"\nOK: {ok}  FAIL: {fail}  TOTAL: {len(entries)}")


if __name__ == "__main__":
    main()