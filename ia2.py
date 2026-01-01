#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Playlist M3U para Archive.org
Extrai vídeos de coleções do Archive.org e gera arquivos M3U compatíveis com players IPTV.

Autor: Modificado para funcionar perfeitamente com Archive.org e GitHub Actions
Data: Janeiro 2026
"""

import subprocess
import json
import os
import sys
from datetime import datetime

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

def get_video_details(url):
    """
    Obtém os detalhes dos vídeos de uma URL do Archive.org usando yt-dlp.
    
    Args:
        url (str): URL da coleção do Archive.org
        
    Returns:
        list: Lista de dicionários contendo detalhes dos vídeos (url, title, thumbnail)
    """
    try:
        log_message(f"Executando yt-dlp para: {url}")
        
        # Usa yt-dlp com --flat-playlist para extrair informações dos vídeos
        result = subprocess.run(
            ['yt-dlp', '-j', '--flat-playlist', url],
            capture_output=True,
            text=True,
            check=True,
            timeout=120  # Timeout de 2 minutos
        )
        
        # Verifica se há saída
        if not result.stdout.strip():
            log_message(f"⚠ Nenhum dado retornado para a URL: {url}")
            return []
        
        # Divide a saída em linhas e converte cada linha JSON em um dicionário
        entries = result.stdout.strip().split('\n')
        details = []
        
        log_message(f"Processando {len(entries)} entrada(s) JSON...")
        
        for entry in entries:
            try:
                data = json.loads(entry)
                details.append(data)
            except json.JSONDecodeError as e:
                log_message(f"⚠ Erro ao decodificar JSON: {e}")
                log_message(f"Linha problemática: {entry[:100]}...")
                continue
        
        log_message(f"✓ Extraídos {len(details)} vídeo(s) com sucesso")
        return details

    except subprocess.TimeoutExpired:
        log_message(f"✗ Timeout ao executar yt-dlp para a URL {url}")
        return []
    
    except subprocess.CalledProcessError as e:
        log_message(f"✗ Erro ao executar yt-dlp para a URL {url}")
        log_message(f"Código de erro: {e.returncode}")
        if e.stderr:
            log_message(f"Stderr: {e.stderr}")
        return []
    
    except FileNotFoundError:
        log_message("="*60)
        log_message("ERRO CRÍTICO: yt-dlp não está instalado no sistema.")
        log_message("="*60)
        log_message("Por favor, instale o yt-dlp com: pip install yt-dlp")
        log_message("="*60)
        sys.exit(1)
    
    except Exception as e:
        log_message(f"✗ Erro inesperado: {type(e).__name__}: {e}")
        return []

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
                file.write("# Nenhum vídeo encontrado\n")
                return
            
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
                    log_message(f"⚠ URL do vídeo não encontrada para: {title}")
        
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
    for i, url in enumerate(urls, 1):
        log_message(f"[{i}/{len(urls)}] Processando: {url}")
        details = get_video_details(url)
        
        if details:
            log_message(f"✓ Encontrados {len(details)} vídeo(s)")
            all_details.extend(details)  # Acumula os detalhes
        else:
            log_message(f"✗ Nenhum vídeo encontrado para esta URL")
        log_message("")
    
    # Escreve o arquivo M3U (mesmo que vazio)
    write_m3u_file(all_details, output_file)
    
    log_message("="*60)
    if all_details:
        log_message(f"✓ SUCESSO: Arquivo '{output_file}' criado com {len(all_details)} vídeo(s)")
    else:
        log_message(f"⚠ AVISO: Arquivo '{output_file}' criado mas nenhum vídeo foi encontrado")
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
    log_message("Gerador de Playlist M3U para Archive.org")
    log_message("Versão com logs para GitHub Actions")
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
