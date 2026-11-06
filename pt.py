# Instalação do Google Chrome, Selenium e as ferramentas de extração de stream (yt-dlp, streamlink) no Colab
!wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
!sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
!apt-get update
!apt-get install -y google-chrome-stable
!pip install selenium yt-dlp streamlink

# Script para baixar e configurar o ChromeDriver correto para a versão do Chrome instalada
import os
import subprocess
import urllib.request
import zipfile
import json
import re

def setup_chromedriver():
    try:
        # Detectar a versão do Google Chrome instalado
        chrome_version = subprocess.check_output(["google-chrome", "--version"]).decode("utf-8").strip()
        print(f"Versão do Google Chrome detectada: {chrome_version}")
        version_number = re.search(r"(\d+\.\d+\.\d+\.\d+)", chrome_version).group(1)

        # Obter a URL correta do ChromeDriver via API do Chrome for Testing
        api_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read().decode())

        # Procurar pela versão estável correspondente
        downloads = data['channels']['Stable']['downloads']['chromedriver']
        download_url = None
        for platform in downloads:
            if platform['platform'] == 'linux64':
                download_url = platform['url']
                break

        if download_url:
            print(f"Baixando o ChromeDriver compatível de: {download_url}")
            urllib.request.urlretrieve(download_url, "chromedriver-linux64.zip")

            # Extrair o zip
            with zipfile.ZipFile("chromedriver-linux64.zip", 'r') as zip_ref:
                zip_ref.extractall("chromedriver_extracted")

            # Mover o executável para o diretório de execução do sistema
            os.system("mv chromedriver_extracted/chromedriver-linux64/chromedriver /usr/local/bin/")
            os.system("chmod +x /usr/local/bin/chromedriver")

            # Limpar arquivos temporários
            os.system("rm -rf chromedriver-linux64.zip chromedriver_extracted")
            print("ChromeDriver instalado e configurado com sucesso!")
        else:
            print("Não foi possível encontrar uma URL de download adequada para o ChromeDriver.")
    except Exception as e:
        print(f"Erro ao configurar o ChromeDriver: {e}")

setup_chromedriver()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# Configure Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280,720")
options.add_argument("--disable-infobars")
options.add_argument("--disable-dev-shm-usage")

# Create the webdriver instance
driver = webdriver.Chrome(options=options)

# URL of the desired page
url_programs = "https://www.rtp.pt/play/programas/tema/rtpmemoria"

# Open the desired page
driver.get(url_programs)

# Wait for the page to load and accept cookies
time.sleep(5)  # Adjust the sleep time if needed to ensure page load

try:
    # Accept cookies if the banner is present
    accept_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Aceitar e fechar')]")
    accept_button.click()
    time.sleep(2)
except:
    pass # Continue if cookie banner is not found

# Scroll down to load more content (RTP Play loads programs dynamically)
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3) # Wait for new content to load
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# Find all relevant video links using regex on href attribute
video_elements = driver.find_elements(By.TAG_NAME, 'a')
video_links = set()

for element in video_elements:
    link = element.get_attribute("href")
    if link and re.search(r'/play/p\d+/e\d+/', link):
        video_links.add(link)

# Prepare to write the links to a file
with open("pt.txt", "w") as file:
    for link in video_links:
        file.write(link + "\n")

# Close the driver
driver.quit()

print("Extração de URLs de páginas de vídeo da RTP Play concluída. As URLs foram salvas em pt.txt")

# Create a new webdriver instance for the second extraction
driver = webdriver.Chrome(options=options)

# URL of the desired page
url_archive = "https://tviplayer.iol.pt/ultimos"

# Open the desired page
driver.get(url_archive)

# Wait for the page to load
time.sleep(5)  # Adjust the sleep time if needed to ensure page load

# Find all relevant video links
video_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')

# Prepare to write the links to a file
with open("pt.txt", "a") as file:
    for element in video_elements:
        link = element.get_attribute("href")
        # Check if the link is valid and not empty
        if link:
            full_link = f"{link}"
            file.write(full_link + "\n")

# Close the driver
driver.quit()

print("Extração de URLs de páginas de vídeo concluída. As URLs foram salvas em pt.txt")

import subprocess
import json
import requests
from bs4 import BeautifulSoup

# Configurações do Selenium (modo headless)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

def get_video_details_youtube(url):
    try:
        result = subprocess.run(
            ['yt-dlp', '-j', '--flat-playlist', url],  # Usando yt-dlp como substituto mais moderno e robusto ao antigo youtube-dl
            capture_output=True,
            text=True,
            check=True
        )
        entries = result.stdout.strip().split('\n')
        return [json.loads(entry) for entry in entries]
    except subprocess.CalledProcessError:
        return []

def get_video_details_yt_dlp(url):
    try:
        result = subprocess.run(
            ['yt-dlp', '-j', '--flat-playlist', url],
            capture_output=True,
            text=True,
            check=True
        )
        entries = result.stdout.strip().split('\n')
        return [json.loads(entry) for entry in entries]
    except subprocess.CalledProcessError:
        return []

def get_video_details_streamlink(url):
    try:
        result = subprocess.run(
            ['streamlink', '--stream-url', url, 'best'],
            capture_output=True,
            text=True,
            check=True
        )
        stream_url = result.stdout.strip()

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"

        return [{'url': stream_url, 'title': title, 'thumbnail': 'N/A'}]
    except (subprocess.CalledProcessError, requests.RequestException):
        return []

def extract_with_selenium(url):
    """Extração de .m3u8, título e thumbnail usando Selenium."""
    try:
        driver_extraction = webdriver.Chrome(options=chrome_options)
        driver_extraction.get(url)
        time.sleep(10)

        title = driver_extraction.title
        logs = driver_extraction.execute_script("return window.performance.getEntriesByType('resource');")
        m3u8_url = next((entry['name'] for entry in logs if ".m3u8" in entry['name']), None)
        thumbnail = next((entry['name'] for entry in logs if entry['name'].endswith('.jpg')), "N/A")

        driver_extraction.quit()

        if m3u8_url:
            return [{
                'url': m3u8_url,
                'title': title.strip(),
                'thumbnail': thumbnail
            }]
        else:
            return []
    except Exception as e:
        print(f"[Selenium] Falha ao extrair com Selenium: {e}")
        return []

def get_video_details(url):
    """Tenta obter os detalhes do vídeo com fallback completo."""
    print(f"Tentando yt-dlp para {url}")
    details = get_video_details_yt_dlp(url)
    if details:
        return details

    print(f"yt-dlp falhou. Tentando youtube-dl para {url}")
    details = get_video_details_youtube(url)
    if details:
        return details

    print(f"youtube-dl falhou. Tentando streamlink para {url}")
    details = get_video_details_streamlink(url)
    if details:
        return details

    print(f"Todos os métodos falharam. Tentando Selenium para {url}")
    details = extract_with_selenium(url)
    if details:
        return details

    print(f"Falha completa ao extrair dados de: {url}")
    return []

def write_m3u_file(details, filename):
    with open(filename, 'a', encoding='utf-8') as file:
        file.write("#EXTM3U\n")
        for entry in details:
            video_url = entry.get('url')
            thumbnail_url = entry.get('thumbnail', 'N/A')
            title = entry.get('title', 'No Title')

            if video_url:
                file.write(f'#EXTINF:-1 tvg-logo="{thumbnail_url}" group-title="VOD PT",{title}\n')
                file.write(f"{video_url}\n")
            else:
                print("URL do vídeo não encontrada.")

def process_urls_from_file(input_file):
    if not os.path.exists(input_file):
        print(f"O arquivo {input_file} não foi encontrado.")
        return

    all_details = []

    with open(input_file, 'r') as file:
        urls = file.readlines()

    urls = [url.strip() for url in urls if url.strip()]

    for i, url in enumerate(urls):
        print(f"\nProcessando URL {i + 1}: {url}")
        details = get_video_details(url)

        if details:
            all_details.extend(details)
        else:
            print(f"Nenhum detalhe encontrado para a URL: {url}")

    filename = 'lista1.m3u'
    write_m3u_file(all_details, filename)
    print(f"\nArquivo {filename} criado com sucesso.")

if __name__ == "__main__":
    input_file = 'pt.txt'
    process_urls_from_file(input_file)
