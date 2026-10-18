#!/usr/bin/env python3
path = '/home/runner/work/1/1/lista1.M3U'
with open(path, encoding='utf-8', errors='ignore') as f:
    content = f.read()

lines = content.splitlines()
out = []
seen_urls = set()
i = 0
n = len(lines)
while i < n:
    s = lines[i].strip()
    if not s:
        i += 1
        continue
    if s.startswith('#EXTM3U'):
        if not out or out[-1] != '#EXTM3U':
            out.append('#EXTM3U')
        i += 1
        continue
    if s.startswith('#EXTINF'):
        # peek next
        j = i + 1
        while j < n and lines[j].strip() == '':
            j += 1
        if j < n:
            url = lines[j].strip()
            if url.startswith(('http://','https://','rtmp://','rtsp://','udp://')):
                if url not in seen_urls:
                    out.append(lines[i])  # keep original line
                    out.append(lines[j])
                    seen_urls.add(url)
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
        continue
    # standalone url
    if s.startswith(('http://','https://','rtmp://','rtsp://','udp://')):
        if s not in seen_urls:
            out.append(lines[i])
            seen_urls.add(s)
    i += 1
    continue

with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')
print('done')
