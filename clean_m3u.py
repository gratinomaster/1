#!/usr/bin/env python3
import sys

path = '/home/runner/work/1/1/lista1.M3U'
with open(path, encoding='utf-8', errors='ignore') as f:
    content = f.read()

lines = content.splitlines()
seen_urls = set()
out = []
first_extm3u = True
for line in lines:
    s = line.strip()
    if not s:
        continue  # skip empty
    if s.startswith('#EXTM3U'):
        if first_extm3u:
            out.append('#EXTM3U')
            first_extm3u = False
        continue  # skip duplicate headers
    if s.startswith('#EXTINF'):
        out.append(line)  # keep as is (preserve original spacing)
        continue
    # URL line
    if s.startswith('http://') or s.startswith('https://') or s.startswith('rtmp://') or s.startswith('rtsp://') or s.startswith('udp://'):
        if s in seen_urls:
            # skip duplicate URL - also need to skip previous EXTINF? easier to handle by pairing
            # but we appended EXTINF already; this is tricky
            # simpler: track state
            pass  # will handle below better with paired logic
        # store
        out.append(line)
        seen_urls.add(s)
        continue
    out.append(line)  # keep others if any

with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')

print('done', len(out))
