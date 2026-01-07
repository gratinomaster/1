#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador Universal de Playlist M3U - Versão Melhorada
Extrai vídeos e streams de sites suportados e agora suporta 1377x.to via vidsrc.
"""

import subprocess
import json
import os
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def log_message(message, log_file='log.txt'):
    """Registra mensagem no arquivo de log e imprime no console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"Erro ao escrever no log: {e}")

def detect_url_type(url):
    """Detecta o tipo de URL para aplicar o método apropriado."""
    url_lower = url.lower()
    if '1377x.to' in url_lower or '1337x.to' in url_lower:
        return '1337x_torrent'
    elif 'archive.org/details/' in url_lower:
        return 'archive_collection'
    elif any(keyword in url_lower for keyword in ['direto', 'live', 'en-vivo', 'ao-vivo', '/live/', '/directo/']):
        return 'live_stream'
    elif any(keyword in url_lower for keyword in ['playlist', 'list=']):
        return 'playlist'
    else:
        return 'single_video'

def extract_from_1337x(url):
    """Extrai o vídeo reproduzível de uma página do 1337x usando vidsrc."""
    try:
        log_message(f"  Tentando extrair vídeo do 1337x: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            log_message(f"  ✗ Erro ao acessar página: Status {response.status_code}")
            return []

        # Procura por ID do IMDb (ttXXXXXXX)
        imdb_id_match = re.search(r'tt\d+', response.text)
        if not imdb_id_match:
            log_message("  ✗ ID do IMDb não encontrado na página")
            return []
        
        imdb_id = imdb_id_match.group(0)
        log_message(f"  ✓ ID do IMDb encontrado: {imdb_id}")
        
        # Constrói o link do vidsrc
        # Nota: vidsrc.net/embed/movie/ID ou vidsrc.net/embed/tv/ID
        # Como padrão, tentamos movie, mas o ideal seria detectar se é série
        vidsrc_url = f"https://vidsrc.net/embed/movie/{imdb_id}"
        
        # Extrai o título da página
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.split('Torrent')[0].strip() if soup.title else f"Video {imdb_id}"
        
        return [{
            'url': vidsrc_url,
            'title': title,
            'thumbnail': 'N/A'
        }]
    except Exception as e:
        log_message(f"  ✗ Erro na extração do 1337x: {e}")
        return []

def extract_with_flat_playlist(url, timeout=120):
    """Extrai informações usando --flat-playlist."""
    try:
        log_message(f"  Tentando método: --flat-playlist")
        result = subprocess.run(
            ['yt-dlp', '-j', '--flat-playlist', url],
            capture_output=True, text=True, check=True, timeout=timeout
        )
        if not result.stdout.strip(): return []
        entries = result.stdout.strip().split('\n')
        details = []
        for entry in entries:
            try:
                data = json.loads(entry)
                details.append(data)
            except json.JSONDecodeError: continue
        return details
    except Exception as e:
        log_message(f"  ✗ Método --flat-playlist falhou: {type(e).__name__}")
        return []

def extract_with_json(url, timeout=120):
    """Extrai informações usando -j."""
    try:
        log_message(f"  Tentando método: -j (JSON completo)")
        result = subprocess.run(
            ['yt-dlp', '-j', '--no-playlist', url],
            capture_output=True, text=True, check=True, timeout=timeout
        )
        if not result.stdout.strip(): return []
        data = json.loads(result.stdout.strip())
        return [data]
    except Exception as e:
        log_message(f"  ✗ Método -j falhou: {type(e).__name__}")
        return []

def extract_with_print_urls(url, timeout=120):
    """Extrai URL direta usando --print urls."""
    try:
        log_message(f"  Tentando método: --print urls")
        result = subprocess.run(
            ['yt-dlp', '--print', 'urls', '--no-playlist', url],
            capture_output=True, text=True, check=True, timeout=timeout
        )
        if not result.stdout.strip(): return []
        stream_url = result.stdout.strip().split('\n')[0]
        domain = urlparse(url).netloc.replace('www.', '')
        return [{
            'url': stream_url,
            'title': f"Stream from {domain}",
            'thumbnail': 'N/A'
        }]
    except Exception as e:
        log_message(f"  ✗ Método --print urls falhou: {type(e).__name__}")
        return []

def get_video_details(url):
    """Obtém os detalhes dos vídeos de uma URL usando estratégia multi-método."""
    log_message(f"Processando URL: {url}")
    url_type = detect_url_type(url)
    log_message(f"  Tipo detectado: {url_type}")
    
    details = []
    if url_type == '1337x_torrent':
        details = extract_from_1337x(url)
    elif url_type == 'archive_collection':
        details = extract_with_flat_playlist(url) or extract_with_json(url)
    elif url_type == 'live_stream':
        details = extract_with_json(url) or extract_with_print_urls(url)
    elif url_type == 'playlist':
        details = extract_with_flat_playlist(url) or extract_with_json(url)
    else:
        details = extract_with_json(url) or extract_with_flat_playlist(url) or extract_with_print_urls(url)
    
    if details:
        log_message(f"  ✓ Extraídos {len(details)} item(s) com sucesso")
    else:
        log_message(f"  ✗ Nenhum item extraído")
    return details

def write_m3u_file(details, filename):
    """Escreve os detalhes dos vídeos no formato M3U."""
    try:
        log_message(f"Criando arquivo M3U: {filename}")
        with open(filename, 'w', encoding='utf-8') as file:
            file.write("#EXTM3U\n")
            if not details:
                file.write("# Nenhum vídeo/stream encontrado\n")
                return
            for entry in details:
                video_url = entry.get('url') or entry.get('webpage_url') or entry.get('id')
                thumbnail_url = entry.get('thumbnail', 'N/A')
                title = entry.get('title', 'No Title')
                if video_url:
                    file.write(f"#EXTINF:-1 tvg-logo=\"{thumbnail_url}\",{title}\n")
                    file.write(f"{video_url}\n")
        log_message(f"✓ Arquivo {filename} criado com sucesso")
    except Exception as e:
        log_message(f"✗ ERRO ao criar arquivo M3U: {e}")

def process_urls_from_file(input_file, output_file='lista30.M3U'):
    """Lê URLs de um arquivo e processa cada uma."""
    log_message("="*60)
    log_message("INICIANDO PROCESSAMENTO")
    log_message("="*60)
    
    if not os.path.exists(input_file):
        log_message(f"✗ ERRO: O arquivo '{input_file}' não foi encontrado.")
        write_m3u_file([], output_file)
        return

    all_details = []
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            urls = [line.strip() for line in file if line.strip() and not line.strip().startswith('#')]
    except Exception as e:
        log_message(f"✗ ERRO ao ler arquivo: {e}")
        write_m3u_file([], output_file)
        return

    for url in urls:
        all_details.extend(get_video_details(url))
    
    write_m3u_file(all_details, output_file)
    log_message("="*60)
    log_message("FIM DO PROCESSAMENTO")
    log_message("="*60)

if __name__ == "__main__":
    input_file = 'urls.txt'
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    process_urls_from_file(input_file)
