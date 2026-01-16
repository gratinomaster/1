import requests

url = "https://drive.usercontent.google.com/uc?id=1zFZUuWtu4Vz4zYhcAAFlvTGrq2zdHApm&export=download"
arquivo_destino = "lista1.M3U"

resposta = requests.get(url)
resposta.raise_for_status()

with open(arquivo_destino, "wb") as arquivo:
    arquivo.write(resposta.content)

print("Download concluído com sucesso!")

import os
import requests
import logging
from logging.handlers import RotatingFileHandler
import json
from bs4 import BeautifulSoup

# Configuração do logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

log_file = "log.txt"
file_handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=5)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Cabeçalho do arquivo M3U
banner = "#EXTM3U\n"

# Função para verificar URLs via requisição HTTP com o agente de usuário do Firefox
def check_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Firefox/89.0"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)  # Usando GET para verificar a URL
        if response.status_code == 200:
            logger.info("URL OK: %s", url)
            return True
        else:
            logger.warning("URL Error %s: Status Code %d", url, response.status_code)
            return False
    except requests.exceptions.RequestException as e:
        logger.error("Request Error %s: %s", url, str(e))
        return False

# Função para processar uma linha #EXTINF
def parse_extinf_line(line):
    group_title = "Undefined"
    tvg_id = "Undefined"
    tvg_logo = "Undefined.png"
    ch_name = "Undefined"
    
    if 'group-title="' in line:
        group_title = line.split('group-title="')[1].split('"')[0]
    if 'tvg-id="' in line:
        tvg_id = line.split('tvg-id="')[1].split('"')[0]
    if 'tvg-logo="' in line:
        tvg_logo = line.split('tvg-logo="')[1].split('"')[0]
    if ',' in line:
        ch_name = line.split(',')[-1].strip()
    
    return ch_name, group_title, tvg_id, tvg_logo

# Função principal para processar o arquivo de entrada
def process_m3u_file(input_file, output_file):
    with open(input_file) as f:
        lines = f.readlines()

    channel_data = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            ch_name, group_title, tvg_id, tvg_logo = parse_extinf_line(line)
            extra_lines = []
            link = None
            
            # Procura pela URL e ignora linhas intermediárias (#EXTVLCOPT, #KODIPROP, etc.)
            while i + 1 < len(lines):
                i += 1
                next_line = lines[i].strip()
                if next_line.startswith('#'):  # Verifica se a linha começa com '#'
                    extra_lines.append(next_line)  # Armazena a linha extra
                else:
                    link = next_line  # Caso contrário, é a URL do canal
                    break
            
            # Verifica a URL antes de adicionar
            if link and check_url(link):
                # Se o canal não tiver logotipo, buscar o logo automaticamente
                if tvg_logo in ["", "N/A", "Undefined.png"]:  # Condição para logo vazio ou "N/A"
                    logo_url = search_google_images(ch_name)
                    if logo_url:
                        tvg_logo = logo_url
                    else:
                        tvg_logo = "NoLogoFound.png"  # Caso não encontre logo
                
                channel_data.append({
                    'name': ch_name,
                    'group': group_title,
                    'tvg_id': tvg_id,
                    'logo': tvg_logo,
                    'url': link,
                    'extra': extra_lines
                })
        i += 1

    # Gera o arquivo de saída M3U
    with open(output_file, "w") as f:  # Certifique-se de usar "w" e não "a" para sobrescrever
        f.write(banner)
        for channel in channel_data:
            extinf_line = (
                f'#EXTINF:-1 group-title="{channel["group"]}" '
                f'tvg-id="{channel["tvg_id"]}" '
                f'tvg-logo="{channel["logo"]}",{channel["name"]}'
            )
            f.write(extinf_line + '\n')
            for extra in channel['extra']:
                f.write(extra + '\n')
            f.write(channel['url'] + '\n')

    # Salva os dados em JSON para análise posterior
    with open("playlist.json", "w") as f:
        json.dump(channel_data, f, indent=2)

# Função para buscar imagem no Google
def search_google_images(query):
    search_url = f"https://www.google.com/search?hl=pt-BR&q={query}&tbm=isch"  # URL de busca de imagens
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        # Buscar a primeira imagem
        img_tags = soup.find_all("img")
        if img_tags:
            # A primeira imagem no Google geralmente é a mais relevante
            img_url = img_tags[1]['src']  # O primeiro item é o logo do Google
            return img_url
    except Exception as e:
        logger.error("Error searching Google images: %s", e)
    
    return None

# Configuração dos arquivos de entrada e saída
input_file = "lista1.M3U"
output_file = "lista1.M3U"

# Executa o processamento
process_m3u_file(input_file, output_file)

import os
import requests

# URLs dos repositórios que contêm os arquivos M3U
repo_urls = [
    "https://api.github.com/repos/gmtv4/rastaf/contents",
    "https://raw.githubusercontent.com/strikeinthehouse/1/refs/heads/main/lista2.M3U",
    "https://github.com/strikeinthehouse/Navez/raw/main/playlist.m3u",
]

lists = []

# Buscar arquivos M3U de cada URL
for url in repo_urls:
    print(f"Processando URL: {url}")
    try:
        response = requests.get(url, allow_redirects=True)

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            
            if url.lower().endswith(('.m3u', '.m3u8')) or '#EXTM3U' in response.text:
                print(f"  Detectado arquivo M3U direto: {url}")
                filename = url.split("/")[-1]
                lists.append((filename, response.text))
            elif 'application/json' in content_type:
                try:
                    contents = response.json()
                    print(f"  Processando resposta JSON com {len(contents)} itens")
                    m3u_files = [content for content in contents if content.get("name", "").lower().endswith(('.m3u', '.m3u8'))]

                    for m3u_file in m3u_files:
                        m3u_url = m3u_file["download_url"]
                        print(f"  Baixando arquivo M3U: {m3u_url}")
                        m3u_response = requests.get(m3u_url, allow_redirects=True)
                        if m3u_response.status_code == 200:
                            lists.append((m3u_file["name"], m3u_response.text))
                except ValueError:
                    print(f"  Erro ao processar JSON de {url}, tratando como arquivo M3U direto")
                    filename = url.split("/")[-1]
                    lists.append((filename, response.text))
            else:
                if '#EXTM3U' in response.text:
                    print(f"  Conteúdo detectado como M3U pelo cabeçalho #EXTM3U")
                    filename = url.split("/")[-1]
                    lists.append((filename, response.text))
                else:
                    print(f"  Tipo de conteúdo não reconhecido: {content_type}")
        else:
            print(f"  Erro ao acessar URL: {url}, código de status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"  Erro ao processar URL {url}: {e}")

# Ordenação dos arquivos M3U pelo nome
lists = sorted(lists, key=lambda x: x[0])

print(f"\nTotal de listas M3U encontradas: {len(lists)}")
for name, _ in lists:
    print(f"  - {name}")

# Limitação das linhas a serem escritas no arquivo final
line_count = 0
output_file = "lista1.M3U"
wrote_header = False  # Para garantir que só escreva uma vez o cabeçalho
epg_urls = []  # Lista para armazenar URLs de EPG encontradas

def extract_epg_url(extm3u_line):
    """Extrai a URL de EPG de uma linha #EXTM3U se presente"""
    if 'url-tvg=' in extm3u_line:
        # Procura por url-tvg="..." ou url-tvg='...'
        import re
        match = re.search(r'url-tvg=["\']([^"\']+)["\']', extm3u_line)
        if match:
            return match.group(1)
    return None

def is_simple_extm3u_header(line):
    """Verifica se é um cabeçalho #EXTM3U simples (sem atributos importantes)"""
    line = line.strip()
    if not line.startswith("#EXTM3U"):
        return False
    
    # Se contém apenas #EXTM3U ou #EXTM3U com espaços, é simples
    if line == "#EXTM3U" or line.replace("#EXTM3U", "").strip() == "":
        return True
    
    # Se contém atributos importantes como url-tvg, não é simples
    important_attributes = ['url-tvg=', 'tvg-url=', 'x-tvg-url=']
    for attr in important_attributes:
        if attr in line.lower():
            return False
    
    return True

with open(output_file, "a") as f:
    for list_name, list_content in lists:
        print(f"Processando lista: {list_name}")
        lines = list_content.split("\n")

        start_idx = 0

        # Verifica se a primeira linha é um cabeçalho #EXTM3U
        if lines and lines[0].strip().startswith("#EXTM3U"):
            if not wrote_header:
                # Escreve o cabeçalho completo com atributos, se presente
                f.write(lines[0].strip() + "\n")
                line_count += 1
                wrote_header = True
                
                # Extrai URL de EPG se presente
                epg_url = extract_epg_url(lines[0])
                if epg_url and epg_url not in epg_urls:
                    epg_urls.append(epg_url)
                    print(f"  URL de EPG encontrada: {epg_url}")
            start_idx = 1  # Pular esta linha nas próximas listas

        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            if not line:
                continue  # Ignorar linhas em branco

            # CORREÇÃO: Distinguir entre cabeçalhos simples e com atributos importantes
            if line.startswith("#EXTM3U"):
                if is_simple_extm3u_header(line):
                    # Ignora apenas cabeçalhos simples duplicados
                    continue
                else:
                    # Preserva cabeçalhos com atributos importantes (como url-tvg)
                    epg_url = extract_epg_url(line)
                    if epg_url and epg_url not in epg_urls:
                        epg_urls.append(epg_url)
                        print(f"  URL de EPG encontrada: {epg_url}")
                    
                    f.write(line + "\n")
                    line_count += 1
                    continue

            f.write(line + "\n")
            line_count += 1

            if line_count >= 212:
                print(f"Limite de 212 linhas atingido")
                break

        if line_count >= 212:
            break

print(f"\nArquivo {output_file} criado com {line_count} linhas")
print(f"URLs de EPG encontradas e preservadas:")
for epg_url in epg_urls:
    print(f"  - {epg_url}")






import requests

repo_urls = [
    "https://github.com/strikeinthehouse/1/raw/refs/heads/main/lista_1.M3U",
    "https://github.com/otoxp/wepg/raw/df55b2ba14f8ec85bd198f85bd3c8cf35d3fa482/list/lista-globos-mitv.m3u
]

lists = []
for url in repo_urls:
    response = requests.get(url)

    if response.status_code == 200:
        if url.endswith(".m3u"):
            lists.append((url.split("/")[-1], response.text))
        else:
            try:
                contents = response.json()

                m3u_files = [content for content in contents if content["name"].endswith(".m3u")]

                for m3u_file in m3u_files:
                    m3u_url = m3u_file["download_url"]
                    m3u_response = requests.get(m3u_url)

                    if m3u_response.status_code == 200:
                        lists.append((m3u_file["name"], m3u_response.text))
            except requests.exceptions.JSONDecodeError:
                print(f"Error parsing JSON from {url}")
    else:
        print(f"Error retrieving contents from {url}")

lists = sorted(lists, key=lambda x: x[0])

line_count = 0
with open("lista1.M3U", "a") as f:
    for l in lists:
        f.write(l[1])
        line_count += l[1].count("\n")
        if line_count >= 200:  # Stop writing after 200 lines
            break


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import youtube_dl
import concurrent.futures

# Configure Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280,720")
options.add_argument("--disable-infobars")


# Create the webdriver instance
driver = webdriver.Chrome(options=options)

# URL of the desired page
url_archive = "https://archive.org/details/television?query=nightly%20news&sort=date"

# Open the desired page
driver.get(url_archive)

# Wait for the page to load
time.sleep(5)

# JavaScript para navegar pelo Shadow DOM e extrair os vídeos
extract_videos_script = """
function deepSearch(root, targetTag) {
    let found = root.querySelector(targetTag);
    if (found) return found;
    
    const elements = root.querySelectorAll('*');
    for (let el of elements) {
        if (el.shadowRoot) {
            found = deepSearch(el.shadowRoot, targetTag);
            if (found) return found;
        }
    }
    return null;
}

const appRoot = document.querySelector('app-root');
if (!appRoot || !appRoot.shadowRoot) {
    return [];
}

const tileDispatcher = deepSearch(appRoot.shadowRoot, 'tile-dispatcher');
if (!tileDispatcher || !tileDispatcher.shadowRoot) {
    return [];
}

const videoInfos = [];
const links = tileDispatcher.shadowRoot.querySelectorAll('a.tile-link');

for (let link of links) {
    const href = link.getAttribute('href');
    const ariaLabel = link.getAttribute('aria-label');
    
    // Tentar pegar a imagem do item-tile
    let thumbnailSrc = '';
    const itemTile = link.querySelector('item-tile');
    if (itemTile && itemTile.shadowRoot) {
        const img = itemTile.shadowRoot.querySelector('img');
        if (img) {
            thumbnailSrc = img.getAttribute('src');
            // Garantir URL absoluta
            if (thumbnailSrc && !thumbnailSrc.startsWith('http')) {
                thumbnailSrc = 'https://archive.org' + thumbnailSrc;
            }
        }
    }
    
    // Garantir URL absoluta para o href
    const fullHref = href.startsWith('http') ? href : 'https://archive.org' + href;
    
    videoInfos.push({
        url: fullHref,
        title: ariaLabel || '',
        thumbnail: thumbnailSrc
    });
}

return videoInfos;
"""

# Executar o script JavaScript para extrair os vídeos
video_infos = []

# Como o site usa carregamento dinâmico, pode ser necessário rolar a página
# para carregar mais vídeos
for scroll_count in range(10):
    # Executar o script para extrair vídeos
    videos = driver.execute_script(extract_videos_script)
    
    # Adicionar novos vídeos à lista (evitando duplicatas)
    existing_urls = {v[0] for v in video_infos}
    for video in videos:
        if video['url'] not in existing_urls:
            video_infos.append((video['url'], video['thumbnail']))
            print("Adicionando URL:", video['url'])
            print("Thumbnail:", video['thumbnail'])
    
    # Rolar para baixo para carregar mais vídeos
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # Se não houver novos vídeos após a rolagem, parar
    if len(videos) == 0:
        break

print(f"\nTotal de vídeos encontrados: {len(video_infos)}")

# Close the webdriver
driver.quit()


# Function to get the direct stream URL and title with error handling
def get_stream_info(url):
    ydl_opts = {
        'quiet': True,
        'format': 'best',
        'noplaylist': True,
        'outtmpl': '/dev/null',
        'geturl': True
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'Video Desconhecido')
            stream_url = info_dict.get('url', '')
            return video_title, stream_url
    except Exception as e:
        print(f"Error fetching info for {url}: {e}")
        return None, None  # Return None for failed entries

# Generate the EXTINF lines with tvg-logo and URLs
with concurrent.futures.ThreadPoolExecutor() as executor:
    results = list(executor.map(lambda info: get_stream_info(info[0]), video_infos))

# Write the EXTINF formatted lines to a file
with open('lista1.M3U', 'a') as file:
    file.write('#EXTM3U\n')  # Add the EXT3MU header
    for (url, thumbnail), (title, stream_url) in zip(video_infos, results):
        if stream_url:
            tvg_logo = f'tvg-logo="{thumbnail}"' if thumbnail else ''
            file.write(f'#EXTINF:-1 group-title="VOD" {tvg_logo},{title}\n{stream_url}\n')

print("A playlist M3U foi gerada com sucesso.")


import requests
from datetime import datetime, timezone, timedelta





# Defina o fuso horário do Brasil
brazil_timezone = timezone(timedelta(hours=-3))

def is_within_time_range(start_time, end_time):
    current_time = datetime.now(brazil_timezone)
    return start_time <= current_time <= end_time

# Horários locais do Brasil para 17h30 e 23h00
start_time_br = datetime.now(brazil_timezone).replace(hour=17, minute=30, second=0, microsecond=0)
end_time_br = datetime.now(brazil_timezone).replace(hour=23, minute=0, second=0, microsecond=0)

# Nome do arquivo de saída
output_file = "lista1.M3U"

if is_within_time_range(start_time_br, end_time_br):
    m3upt_url = "https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u"
    m3upt_response = requests.get(m3upt_url)

    if m3upt_response.status_code == 200:
        m3upt_lines = m3upt_response.text.split('\n')[:25]

        with open(output_file, "a") as f:
            for line in m3upt_lines:
                f.write(line + '\n')
else:
    with open(output_file, "a") as f:
        f.write("#EXTM3U\n")

