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



