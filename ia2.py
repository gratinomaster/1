#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador Universal de Playlist M3U
Extrai vídeos e streams de qualquer site suportado pelo yt-dlp e gera arquivos M3U.

Suporta:
- Archive.org (coleções com múltiplos vídeos)
- Streams ao vivo (RTP, TVI, RTVE, YouTube Live, etc)
- Vídeos únicos (YouTube, Vimeo, etc)
- Playlists (YouTube, etc)
- Qualquer site suportado pelo yt-dlp

Autor: Versão Universal para GitHub Actions
Data: Janeiro 2026
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

def log_message(message, log_file='log.txt'):
    """
    Registra mensagem no arquivo de log e imprime no console.
    
    Args:
        message (str): Mensagem a ser registrada
        log_file (str): Nome do arquivo de log
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"Erro ao escrever no log: {e}")

def detect_url_type(url):
    """
    Detecta o tipo de URL para aplicar o método apropriado de extração.
    
    Args:
        url (str): URL a ser analisada
        
    Returns:
        str: Tipo da URL ('archive_collection', 'live_stream', 'playlist', 'single_video')
    """
    url_lower = url.lower()
    
    if 'archive.org/details/' in url_lower:
        return 'archive_collection'
    elif any(keyword in url_lower for keyword in ['direto', 'live', 'en-vivo', 'ao-vivo', '/live/', '/directo/']):
        return 'live_stream'
    elif any(keyword in url_lower for keyword in ['playlist', 'list=']):
        return 'playlist'
    else:
        return 'single_video'

def extract_with_flat_playlist(url, timeout=120):
    """
    Extrai informações usando --flat-playlist (para coleções/playlists).
    
    Args:
        url (str): URL a ser processada
        timeout (int): Timeout em segundos
        
    Returns:
        list: Lista de dicionários com informações dos vídeos
    """
    try:
        log_message(f"  Tentando método: --flat-playlist")
        
        result = subprocess.run(
            ['yt-dlp', '-j', '--flat-playlist', url],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        
        if not result.stdout.strip():
            return []
        
        entries = result.stdout.strip().split('\n')
        details = []
        
        for entry in entries:
            try:
                data = json.loads(entry)
                details.append(data)
            except json.JSONDecodeError:
                continue
        
        return details
    
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception) as e:
        log_message(f"  ✗ Método --flat-playlist falhou: {type(e).__name__}")
        return []

def extract_with_json(url, timeout=120):
    """
    Extrai informações usando -j sem --flat-playlist (para vídeos únicos/streams).
    
    Args:
        url (str): URL a ser processada
        timeout (int): Timeout em segundos
        
    Returns:
        list: Lista com um dicionário contendo informações do vídeo/stream
    """
    try:
        log_message(f"  Tentando método: -j (JSON completo)")
        
        result = subprocess.run(
            ['yt-dlp', '-j', '--no-playlist', url],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        
        if not result.stdout.strip():
            return []
        
        data = json.loads(result.stdout.strip())
        return [data]
    
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        log_message(f"  ✗ Método -j falhou: {type(e).__name__}")
        return []

def extract_with_print_urls(url, timeout=120):
    """
    Extrai URL direta usando --print urls (fallback simples).
    
    Args:
        url (str): URL a ser processada
        timeout (int): Timeout em segundos
        
    Returns:
        list: Lista com um dicionário contendo URL e título básico
    """
    try:
        log_message(f"  Tentando método: --print urls")
        
        result = subprocess.run(
            ['yt-dlp', '--print', 'urls', '--no-playlist', url],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        
        if not result.stdout.strip():
            return []
        
        stream_url = result.stdout.strip().split('\n')[0]
        
        # Extrai nome do domínio para usar como título
        domain = urlparse(url).netloc.replace('www.', '')
        title = f"Stream from {domain}"
        
        return [{
            'url': stream_url,
            'title': title,
            'thumbnail': 'N/A'
        }]
    
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception) as e:
        log_message(f"  ✗ Método --print urls falhou: {type(e).__name__}")
        return []

def get_video_details(url):
    """
    Obtém os detalhes dos vídeos de uma URL usando estratégia multi-método.
    
    Args:
        url (str): URL a ser processada
        
    Returns:
        list: Lista de dicionários contendo detalhes dos vídeos (url, title, thumbnail)
    """
    log_message(f"Processando URL: {url}")
    
    # Detecta o tipo de URL
    url_type = detect_url_type(url)
    log_message(f"  Tipo detectado: {url_type}")
    
    details = []
    
    # Estratégia baseada no tipo de URL
    if url_type == 'archive_collection':
        # Archive.org: tenta --flat-playlist primeiro
        details = extract_with_flat_playlist(url)
        if not details:
            details = extract_with_json(url)
    
    elif url_type == 'live_stream':
        # Streams ao vivo: tenta -j primeiro, depois --print urls
        details = extract_with_json(url)
        if not details:
            details = extract_with_print_urls(url)
    
    elif url_type == 'playlist':
        # Playlists: tenta --flat-playlist primeiro
        details = extract_with_flat_playlist(url)
        if not details:
            details = extract_with_json(url)
    
    else:
        # Vídeos únicos: tenta -j primeiro
        details = extract_with_json(url)
        if not details:
            details = extract_with_flat_playlist(url)
        if not details:
            details = extract_with_print_urls(url)
    
    # Log do resultado
    if details:
        log_message(f"  ✓ Extraídos {len(details)} item(s) com sucesso")
    else:
        log_message(f"  ✗ Nenhum item extraído")
    
    return details

def write_m3u_file(details, filename):
    """
    Escreve os detalhes dos vídeos no formato M3U em um arquivo.
    Sempre cria o arquivo, mesmo que a lista esteja vazia.
    
    Args:
        details (list): Lista de dicionários com informações dos vídeos
        filename (str): Nome do arquivo M3U a ser criado
    """
    try:
        log_message(f"Criando arquivo M3U: {filename}")
        
        with open(filename, 'w', encoding='utf-8') as file:
            # Adiciona o cabeçalho #EXTM3U
            file.write("#EXTM3U\n")
            
            if not details:
                log_message("⚠ Lista de vídeos vazia, criando arquivo M3U vazio")
                file.write("# Nenhum vídeo/stream encontrado\n")
                return
            
            # Adiciona os detalhes dos vídeos no formato M3U
            for entry in details:
                video_url = entry.get('url')
                thumbnail_url = entry.get('thumbnail', 'N/A')
                title = entry.get('title', 'No Title')
                
                # Se a URL estiver vazia, tenta pegar do campo 'webpage_url' ou 'id'
                if not video_url:
                    video_url = entry.get('webpage_url') or entry.get('id')
                
                if video_url:
                    # Formata e escreve o título e o URL no formato #EXTINF
                    file.write(f"#EXTINF:-1 tvg-logo=\"{thumbnail_url}\",{title}\n")
                    file.write(f"{video_url}\n")
                else:
                    log_message(f"  ⚠ URL não encontrada para: {title}")
        
        log_message(f"✓ Arquivo {filename} criado com sucesso")
        
    except Exception as e:
        log_message(f"✗ ERRO ao criar arquivo M3U: {type(e).__name__}: {e}")
        raise

def process_urls_from_file(input_file, output_file='lista30.M3U'):
    """
    Lê URLs de um arquivo e processa cada uma para criar um único arquivo M3U.
    
    Args:
        input_file (str): Caminho do arquivo contendo as URLs (uma por linha)
        output_file (str): Nome do arquivo M3U a ser gerado (padrão: lista30.M3U)
    """
    log_message("="*60)
    log_message("INICIANDO PROCESSAMENTO")
    log_message("="*60)
    
    # Verifica se o arquivo de entrada existe
    if not os.path.exists(input_file):
        log_message(f"✗ ERRO: O arquivo '{input_file}' não foi encontrado.")
        log_message(f"Diretório atual: {os.getcwd()}")
        log_message(f"Arquivos no diretório: {os.listdir('.')}")
        
        # Cria arquivo M3U vazio mesmo assim
        log_message("Criando arquivo M3U vazio devido à falta do arquivo de entrada")
        write_m3u_file([], output_file)
        return
    
    log_message(f"✓ Arquivo de entrada encontrado: {input_file}")
    
    all_details = []  # Lista para acumular todos os detalhes dos vídeos
    
    # Lê as URLs do arquivo
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            urls = file.readlines()
        
        log_message(f"Total de linhas lidas: {len(urls)}")
    except Exception as e:
        log_message(f"✗ ERRO ao ler arquivo: {type(e).__name__}: {e}")
        write_m3u_file([], output_file)
        return
    
    # Remove espaços em branco, linhas vazias e comentários
    urls = [url.strip() for url in urls if url.strip() and not url.strip().startswith('#')]
    
    if not urls:
        log_message(f"✗ ERRO: Nenhuma URL válida encontrada no arquivo '{input_file}'")
        log_message("Criando arquivo M3U vazio")
        write_m3u_file([], output_file)
        return
    
    log_message(f"Encontradas {len(urls)} URL(s) válida(s) para processar")
    log_message("")
    
    # Processa cada URL
    success_count = 0
    fail_count = 0
    
    for i, url in enumerate(urls, 1):
        log_message(f"[{i}/{len(urls)}] Processando: {url}")
        details = get_video_details(url)
        
        if details:
            log_message(f"  ✓ Sucesso: {len(details)} item(s)")
            all_details.extend(details)
            success_count += 1
        else:
            log_message(f"  ✗ Falha: nenhum item extraído")
            fail_count += 1
        log_message("")
    
    # Escreve o arquivo M3U (mesmo que vazio)
    write_m3u_file(all_details, output_file)
    
    log_message("="*60)
    log_message(f"RESUMO DO PROCESSAMENTO:")
    log_message(f"  URLs processadas: {len(urls)}")
    log_message(f"  Sucessos: {success_count}")
    log_message(f"  Falhas: {fail_count}")
    log_message(f"  Total de itens extraídos: {len(all_details)}")
    
    if all_details:
        log_message(f"✓ SUCESSO: Arquivo '{output_file}' criado com {len(all_details)} item(s)")
    else:
        log_message(f"⚠ AVISO: Arquivo '{output_file}' criado mas nenhum item foi encontrado")
    log_message("="*60)
    
    # Verifica se o arquivo foi realmente criado
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        log_message(f"✓ Arquivo confirmado: {output_file} ({file_size} bytes)")
    else:
        log_message(f"✗ ERRO: Arquivo {output_file} não foi criado!")

def main():
    """Função principal do programa."""
    log_message("="*60)
    log_message("Gerador Universal de Playlist M3U")
    log_message("Suporta Archive.org, Streams ao vivo, e qualquer site do yt-dlp")
    log_message("="*60)
    log_message("")
    
    # Nome do arquivo contendo os URLs (padrão)
    input_file = 'ia.txt'
    output_file = 'lista30.M3U'
    
    # Verifica se foram passados argumentos na linha de comando
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        log_message(f"Arquivo de entrada (argumento): {input_file}")
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
        log_message(f"Arquivo de saída (argumento): {output_file}")
    
    log_message(f"Configuração:")
    log_message(f"  - Entrada: {input_file}")
    log_message(f"  - Saída: {output_file}")
    log_message(f"  - Diretório: {os.getcwd()}")
    log_message("")
    
    # Verifica se yt-dlp está instalado
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        log_message(f"yt-dlp versão: {result.stdout.strip()}")
    except FileNotFoundError:
        log_message("="*60)
        log_message("ERRO CRÍTICO: yt-dlp não está instalado no sistema.")
        log_message("="*60)
        log_message("Por favor, instale o yt-dlp com: pip install yt-dlp")
        log_message("="*60)
        sys.exit(1)
    
    log_message("")
    
    # Processa URLs do arquivo
    try:
        process_urls_from_file(input_file, output_file)
    except Exception as e:
        log_message(f"✗ ERRO FATAL: {type(e).__name__}: {e}")
        import traceback
        log_message(traceback.format_exc())
        sys.exit(1)
    
    log_message("")
    log_message("="*60)
    log_message("PROCESSAMENTO FINALIZADO")
    log_message("="*60)

if __name__ == "__main__":
    main()
