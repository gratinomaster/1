#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Playlist M3U para Archive.org
Extrai vídeos de coleções do Archive.org e gera arquivos M3U compatíveis com players IPTV.

Autor: Modificado para funcionar perfeitamente com Archive.org
Data: Janeiro 2026
"""

import subprocess
import json
import os
import sys

def get_video_details(url):
    """
    Obtém os detalhes dos vídeos de uma URL do Archive.org usando yt-dlp.
    
    Args:
        url (str): URL da coleção do Archive.org
        
    Returns:
        list: Lista de dicionários contendo detalhes dos vídeos (url, title, thumbnail)
    """
    try:
        # Usa yt-dlp com --flat-playlist para extrair informações dos vídeos
        result = subprocess.run(
            ['yt-dlp', '-j', '--flat-playlist', url],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Verifica se há saída
        if not result.stdout.strip():
            print(f"  ⚠ Nenhum dado retornado para a URL: {url}")
            return []
        
        # Divide a saída em linhas e converte cada linha JSON em um dicionário
        entries = result.stdout.strip().split('\n')
        details = []
        
        for entry in entries:
            try:
                data = json.loads(entry)
                details.append(data)
            except json.JSONDecodeError as e:
                print(f"  ⚠ Erro ao decodificar JSON: {e}")
                print(f"  Linha problemática: {entry[:100]}...")
                continue
        
        return details

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Erro ao executar yt-dlp para a URL {url}")
        print(f"  Código de erro: {e.returncode}")
        if e.stderr:
            print(f"  Stderr: {e.stderr}")
        return []
    
    except FileNotFoundError:
        print("\n" + "="*60)
        print("ERRO: yt-dlp não está instalado no sistema.")
        print("="*60)
        print("\nPor favor, instale o yt-dlp com um dos seguintes comandos:")
        print("  • pip install yt-dlp")
        print("  • pip3 install yt-dlp")
        print("  • sudo pip3 install yt-dlp")
        print("\nOu visite: https://github.com/yt-dlp/yt-dlp")
        print("="*60 + "\n")
        sys.exit(1)

def write_m3u_file(details, filename):
    """
    Escreve os detalhes dos vídeos no formato M3U em um arquivo.
    
    Args:
        details (list): Lista de dicionários com informações dos vídeos
        filename (str): Nome do arquivo M3U a ser criado
    """
    with open(filename, 'w', encoding='utf-8') as file:
        # Adiciona o cabeçalho #EXTM3U
        file.write("#EXTM3U\n")
        
        # Adiciona os detalhes dos vídeos no formato M3U
        for entry in details:
            video_url = entry.get('url')
            thumbnail_url = entry.get('thumbnail', 'N/A')
            title = entry.get('title', 'No Title')  # Obtém o título do vídeo

            if video_url:
                # Formata e escreve o título e o URL no formato #EXTINF
                file.write(f"#EXTINF:-1 tvg-logo=\"{thumbnail_url}\",{title}\n")
                file.write(f"{video_url}\n")
            else:
                print(f"  ⚠ URL do vídeo não encontrada para: {title}")

def process_urls_from_file(input_file, output_file='lista30.M3U'):
    """
    Lê URLs de um arquivo e processa cada uma para criar um único arquivo M3U.
    
    Args:
        input_file (str): Caminho do arquivo contendo as URLs (uma por linha)
        output_file (str): Nome do arquivo M3U a ser gerado (padrão: lista30.M3U)
    """
    if not os.path.exists(input_file):
        print(f"\n✗ ERRO: O arquivo '{input_file}' não foi encontrado.\n")
        return
    
    all_details = []  # Lista para acumular todos os detalhes dos vídeos
    
    # Lê as URLs do arquivo
    with open(input_file, 'r', encoding='utf-8') as file:
        urls = file.readlines()
    
    # Remove espaços em branco, linhas vazias e comentários
    urls = [url.strip() for url in urls if url.strip() and not url.strip().startswith('#')]
    
    if not urls:
        print(f"\n✗ ERRO: Nenhuma URL válida encontrada no arquivo '{input_file}'\n")
        return
    
    print(f"Encontradas {len(urls)} URL(s) para processar.\n")
    
    # Processa cada URL
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Processando: {url}")
        details = get_video_details(url)
        
        if details:
            print(f"  ✓ Encontrados {len(details)} vídeo(s)")
            all_details.extend(details)  # Acumula os detalhes
        else:
            print(f"  ✗ Nenhum vídeo encontrado para esta URL")
        print()
    
    # Verifica se há vídeos para escrever
    if not all_details:
        print("✗ ERRO: Nenhum vídeo foi encontrado em nenhuma das URLs.\n")
        return
    
    # Escreve todos os detalhes acumulados em um único arquivo M3U
    write_m3u_file(all_details, output_file)
    
    print("=" * 60)
    print(f"✓ Arquivo '{output_file}' criado com sucesso!")
    print(f"  Total de vídeos no arquivo M3U: {len(all_details)}")
    print("=" * 60)

def main():
    """Função principal do programa."""
    print("=" * 60)
    print("Gerador de Playlist M3U para Archive.org")
    print("=" * 60)
    print()
    
    # Nome do arquivo contendo os URLs (padrão)
    input_file = 'ia.txt'
    output_file = 'lista30.M3U'
    
    # Verifica se foram passados argumentos na linha de comando
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Processa URLs do arquivo
    process_urls_from_file(input_file, output_file)

if __name__ == "__main__":
    main()
