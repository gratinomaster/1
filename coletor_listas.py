#!/usr/bin/env python3
"""Coleta canais das fontes configuradas e reescreve a playlist lista1.M3U.

Comportamento:
  * o arquivo de saida e reescrito a cada execucao (os canais anteriores sao
    apagados antes de gravar os novos);
  * fontes indisponiveis ou fora do periodo de atualizacao mantem os dados que
    ja existiam no arquivo (preservacao);
  * os intervalos de horario usam o fuso America/Sao_Paulo.

As fontes ficam nas constantes A a E abaixo, na mesma ordem do pedido.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time as hora, timezone, timedelta
from urllib.parse import parse_qs, quote, urlparse

import requests

try:
    from zoneinfo import ZoneInfo

    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:  # sem tzdata no sistema
    FUSO = timezone(timedelta(hours=-3))

FUSO_NOME = "America/Sao_Paulo"
ARQUIVOS_SAIDA = ("lista1.M3U", "lista1.m3u")
TIMEOUT = 30
TRABALHADORES = 10
MAX_VOD = 20
CABECALHO = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEADERS = {"User-Agent": CABECALHO, "Accept": "*/*"}

# ---------------------------------------------------------------------------
# A. Listas diretas (URLs que ja apontam para arquivos, ou paginas /contents,
#    que sao resolvidas pela API do GitHub)
# ---------------------------------------------------------------------------
M3U_SOURCES = [
    "https://github.com/gmtv4/rastaf/contents",
    "https://github.com/gratinomaster/1/raw/refs/heads/main/lista2.M3U",
    "https://github.com/iptv-org/iptv/raw/6b77242580c3b34d34f984265bfed2937708fce0/streams/us_moveonjoy.m3u",
    "https://github.com/strikeinthehouse/1/raw/refs/heads/main/lista_1.M3U",
    "https://github.com/otoxp/wepg/raw/df55b2ba14f8ec85bd198f85bd3c8cf35d3fa482/list/lista-globos-mitv.m3u",
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/REALITY.m3u",
    "https://github.com/iprtl/m3u/raw/b8507db8229defeda88512eaaf66bfe0e385e81c/Freetv.m3u",
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u",
    "https://github.com/punkrastafari/neta/raw/refs/heads/main/lista_final.m3u",
]

# ---------------------------------------------------------------------------
# B. Repositorios consultados pela API do GitHub (arquivos .m3u / .m3u8)
# ---------------------------------------------------------------------------
GITHUB_API_SOURCES = [
    "https://api.github.com/repos/gmtv4/rastaf/contents",
    "https://api.github.com/repos/gratinomaster/JCTV/contents",
    "https://api.github.com/repos/strikeinthehouse/YT-OK/contents",
    "https://api.github.com/repos/punkstarbr/STR-YT/contents",
]

# ---------------------------------------------------------------------------
# C. Fontes para atualizacao programada.
#    "windows" = intervalos ["HH:MM", "HH:MM"] (podem cruzar a meia-noite);
#    "weekdays" = dias permitidos (0 = segunda ... 6 = domingo), opcional.
#    Edite os intervalos conforme a sua necessidade.
# ---------------------------------------------------------------------------
SCHEDULED_M3U_SOURCES = [
    {
        "url": "https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u",
        "windows": [("17:30", "23:00")],
    },
    {
        "url": "https://github.com/strikeinthehouse/1/raw/main/lista2.M3U",
        "windows": [("11:30", "13:30"), ("19:00", "19:45"), ("17:30", "20:00")],
        "weekdays": (0, 1, 2, 3, 4, 5),
    },
    {
        "url": "https://github.com/punkstarbr/STR-YT/raw/main/lista1.M3U",
        "windows": [("06:00", "23:59")],
    },
    {
        "url": "https://github.com/strikeinthehouse/M3UPT/raw/main/M3U/M3UPT.m3u",
        "windows": [("06:00", "23:59")],
    },
]

# ---------------------------------------------------------------------------
# D. Videos VOD do Internet Archive (ponto inicial de pesquisa)
# ---------------------------------------------------------------------------
VOD_SOURCES = [
    "https://archive.org/details/television?query=cbs&sort=date&tab=collection",
]

# ---------------------------------------------------------------------------
# E. Fontes adicionais para coleta de playlists
# ---------------------------------------------------------------------------
ADDITIONAL_M3U_SOURCES = [
    "https://github.com/punkstarbr/STR-YT/raw/refs/heads/main/REALITY.m3u",
    "https://github.com/iprtl/m3u/raw/b8507db8229defeda88512eaaf66bfe0e385e81c/Freetv.m3u",
    "https://github.com/ipstreet312/freeiptv/raw/refs/heads/master/all.m3u",
    "https://github.com/punkrastafari/neta/raw/refs/heads/main/lista_final.m3u",
]

# ordem de preferencia dos formatos reproduziveis
ORDEM_VIDEO = (".mp4", ".m4v", ".webm", ".ogv", ".mkv", ".avi", ".mpeg", ".mpg")


def log(mensagem):
    print(mensagem, flush=True)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def baixar_texto(url, timeout=TIMEOUT):
    try:
        resposta = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    except requests.RequestException as erro:
        log(f"    falha em {url}: {erro}")
        return None
    if resposta.status_code != 200:
        log(f"    HTTP {resposta.status_code} em {url}")
        return None
    return resposta.text


def url_listagem(url):
    """Converte paginas github.com/<donorepo>/contents na URL da API."""
    achado = re.match(
        r"https?://github\.com/([^/]+)/([^/?#]+)/contents(?:/([^?#]*))?", url
    )
    if not achado:
        return url
    dono, repo, caminho = achado.group(1), achado.group(2), achado.group(3) or ""
    api = f"https://api.github.com/repos/{dono}/{repo}/contents"
    return f"{api}/{caminho}" if caminho else api


# ---------------------------------------------------------------------------
# M3U
# ---------------------------------------------------------------------------
def parse_m3u(texto):
    """Devolve (cabecalhos, entradas); cada entrada e a lista de linhas."""
    cabecalhos = []
    entradas = []
    linhas = [linha.strip() for linha in texto.splitlines()]
    indice = 0
    while indice < len(linhas):
        linha = linhas[indice]
        indice += 1
        if not linha:
            continue
        if linha.startswith("#EXTM3U"):
            cabecalhos.append(linha)
            continue
        if not linha.startswith("#EXTINF"):
            continue
        bloco = [linha]
        url = None
        while indice < len(linhas):
            proxima = linhas[indice]
            indice += 1
            if not proxima:
                continue
            if proxima.startswith("#"):
                bloco.append(proxima)
                continue
            url = proxima
            break
        if url:
            bloco.append(url)
            entradas.append(bloco)
    return cabecalhos, entradas


def url_da_entrada(bloco):
    return bloco[-1]


def nome_da_entrada(bloco):
    for linha in bloco:
        if linha.startswith("#EXTINF") and "," in linha:
            return linha.rsplit(",", 1)[-1].strip()
    return ""


def entradas_de(textos):
    todas = []
    for _nome, texto in textos:
        _cabecalhos, entradas = parse_m3u(texto)
        todas.extend(entradas)
    return todas


def cabecalho_final(novos_cabecalhos, cabecalhos_antigos):
    epg = []

    def coletar(linha):
        for atributo in ("url-tvg", "tvg-url", "x-tvg-url"):
            achado = re.search(
                rf'{atributo}\s*=\s*["\']([^"\']+)["\']', linha, flags=re.IGNORECASE
            )
            if achado:
                epg.extend(re.split(r"[,\s|]+", achado.group(1)))

    for linha in novos_cabecalhos + cabecalhos_antigos:
        coletar(linha)
    epg_unicos = [item for item in dict.fromkeys(epg) if item]
    if epg_unicos:
        return '#EXTM3U url-tvg="' + ",".join(epg_unicos) + '"'
    for linha in novos_cabecalhos + cabecalhos_antigos:
        if linha.strip() != "#EXTM3U":
            return linha.strip()
    return "#EXTM3U"


# ---------------------------------------------------------------------------
# Fontes de playlist
# ---------------------------------------------------------------------------
def baixar_arquivos_m3u(arquivos):
    """Baixa (nome, download_url) em paralelo; mantem so playlists validas."""
    validos = []

    def baixar(item):
        nome, link = item
        texto = baixar_texto(link)
        if texto and "#EXTM3U" in texto:
            return (nome, texto)
        return None

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(arquivos)))) as pool:
        for resultado in pool.map(baixar, arquivos):
            if resultado:
                validos.append(resultado)
    return validos


def coletar_fonte(url):
    """Baixa uma fonte. Devolve [(nome, texto)] ou None se indisponivel."""
    alvo = url_listagem(url)

    if alvo.lower().endswith((".m3u", ".m3u8")):
        texto = baixar_texto(alvo)
        if not texto or "#EXTM3U" not in texto:
            return None
        return [(alvo.rsplit("/", 1)[-1], texto)]

    texto = baixar_texto(alvo)
    if texto is None:
        return None

    dados = None
    try:
        dados = json.loads(texto)
    except ValueError:
        dados = None

    if isinstance(dados, (dict, list)):
        itens = dados if isinstance(dados, list) else [dados]
        arquivos = []
        for item in itens:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("name") or "")
            link = item.get("download_url")
            if link and nome.lower().endswith((".m3u", ".m3u8")):
                arquivos.append((nome, link))
        if not arquivos:
            # diretorio valido, porem sem playlists
            return [] if isinstance(dados, list) else None
        return baixar_arquivos_m3u(arquivos)

    if "#EXTM3U" in texto:
        return [(alvo.rsplit("/", 1)[-1], texto)]
    return None


def coletar_em_paralelo(urls):
    resultados = {}
    with ThreadPoolExecutor(max_workers=TRABALHADORES) as pool:
        futuros = {pool.submit(coletar_fonte, url): url for url in urls}
        for futuro in as_completed(futuros):
            url = futuros[futuro]
            try:
                resultados[url] = futuro.result()
            except Exception as erro:  # noqa: BLE001
                log(f"    erro ao processar {url}: {erro}")
                resultados[url] = None
    return resultados


# ---------------------------------------------------------------------------
# Horarios agendados
# ---------------------------------------------------------------------------
def hora_minuto(valor):
    partes = valor.split(":")
    return hora(int(partes[0]), int(partes[1]))


def dentro_do_periodo(agora, especificacao):
    dias = especificacao.get("weekdays")
    if dias is not None and agora.weekday() not in dias:
        return False
    atual = agora.time().replace(microsecond=0)
    for inicio, fim in especificacao.get("windows", ()):
        inicio_h = hora_minuto(inicio)
        fim_h = hora_minuto(fim)
        if inicio_h <= fim_h:
            if inicio_h <= atual <= fim_h:
                return True
        elif atual >= inicio_h or atual <= fim_h:
            return True
    return False


# ---------------------------------------------------------------------------
# VOD - Internet Archive
# ---------------------------------------------------------------------------
def titulo_de(valor):
    if isinstance(valor, (list, tuple)):
        valor = next((item for item in valor if item), None)
    if isinstance(valor, str):
        valor = valor.strip()
    return valor or None


def arquivo_reproduzivel(arquivos):
    candidatos = [
        item
        for item in arquivos
        if str(item.get("name") or "").lower().endswith(ORDEM_VIDEO)
    ]
    if not candidatos:
        return None
    for extensao in ORDEM_VIDEO:
        for item in candidatos:
            if str(item.get("name")).lower().endswith(extensao):
                return item
    return None


def miniatura_do(identifier, doc):
    capa = doc.get("thumbnail")
    if isinstance(capa, str) and capa.startswith("http"):
        return capa
    candidata = f"https://archive.org/services/img/{identifier}"
    try:
        resposta = requests.head(
            candidata, headers=HEADERS, timeout=15, allow_redirects=True
        )
        if resposta.status_code == 200:
            return candidata
    except requests.RequestException:
        pass
    return None


def item_vod(doc):
    """Monta a entrada de um item do Internet Archive, se for video valido."""
    identifier = doc.get("identifier")
    if not identifier:
        return None

    texto = baixar_texto(f"https://archive.org/metadata/{identifier}")
    if texto is None:
        return None
    try:
        meta = json.loads(texto)
    except ValueError:
        return None

    arquivo = arquivo_reproduzivel(meta.get("files") or [])
    if not arquivo:
        return None

    titulo = titulo_de(doc.get("title")) or titulo_de(meta.get("title"))
    if not titulo:
        return None

    nome_arquivo = str(arquivo.get("name"))
    reproducao = (
        f"https://archive.org/download/{identifier}/{quote(nome_arquivo, safe='/')}"
    )
    logo = miniatura_do(identifier, doc)
    atributos = f'tvg-id="{identifier}"'
    if logo:
        atributos += f' tvg-logo="{logo}"'
    atributos += ' group-title="VOD"'
    return [f"#EXTINF:-1 {atributos},{titulo}", reproducao]


def coletar_vod(pagina):
    """Pesquisa na pagina inicial e devolve as entradas reproduziveis."""
    partes = [parte for parte in urlparse(pagina).path.split("/") if parte]
    colecao = partes[1] if len(partes) >= 2 and partes[0] == "details" else ""
    termo = (parse_qs(urlparse(pagina).query).get("query") or [""])[0].strip()

    termos = []
    if colecao:
        termos.append(f"collection:{colecao}")
    if termo:
        termos.append(termo)
    termos.append("mediatype:movies")

    try:
        resposta = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": " AND ".join(termos),
                "fl[]": ["identifier", "title", "thumbnail", "date"],
                "sort[]": "date desc",
                "rows": MAX_VOD,
                "output": "json",
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
    except requests.RequestException as erro:
        log(f"    falha na pesquisa VOD: {erro}")
        return None
    if resposta.status_code != 200:
        log(f"    HTTP {resposta.status_code} na pesquisa VOD")
        return None

    try:
        documentos = resposta.json().get("response", {}).get("docs", [])
    except ValueError:
        return None
    if not documentos:
        return []

    entradas = []
    with ThreadPoolExecutor(max_workers=TRABALHADORES) as pool:
        for resultado in pool.map(item_vod, documentos):
            if resultado:
                entradas.append(resultado)
    return entradas


# ---------------------------------------------------------------------------
# Arquivo de saida
# ---------------------------------------------------------------------------
def ler_saida():
    for caminho in ARQUIVOS_SAIDA:
        try:
            with open(caminho, encoding="utf-8", errors="replace") as arquivo:
                texto = arquivo.read()
        except OSError:
            continue
        return parse_m3u(texto)
    return [], []


def gravar_saida(cabecalho, entradas):
    linhas = [cabecalho]
    for entrada in entradas:
        linhas.extend(entrada)
    conteudo = "\n".join(linhas) + "\n"
    for caminho in ARQUIVOS_SAIDA:
        with open(caminho, "w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(conteudo)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main():
    agora = datetime.now(FUSO)
    log(f"Execucao em {agora.strftime('%Y-%m-%d %H:%M:%S')} ({FUSO_NOME})")

    cabecalhos_antigos, entradas_antigas = ler_saida()
    log(
        f"Arquivo existente: {len(entradas_antigas)} canais "
        f"(serao substituidos, exceto os preservados)"
    )

    # monta a lista de fontes: grupo, url e se entra nesta atualizacao
    tarefas = []
    for url in M3U_SOURCES:
        tarefas.append({"grupo": "A", "url": url, "escrever": True})
    for url in GITHUB_API_SOURCES:
        tarefas.append({"grupo": "B", "url": url, "escrever": True})
    for especificacao in SCHEDULED_M3U_SOURCES:
        url = especificacao["url"]
        dentro = dentro_do_periodo(agora, especificacao)
        tarefas.append({"grupo": "C", "url": url, "escrever": dentro})
        situacao = "atualizando" if dentro else "fora do periodo -> preserva dados"
        log(f"C {situacao}: {url}")
    for url in ADDITIONAL_M3U_SOURCES:
        tarefas.append({"grupo": "E", "url": url, "escrever": True})

    urls = list(dict.fromkeys(tarefa["url"] for tarefa in tarefas))
    log(f"Baixando {len(urls)} fontes de playlist...")
    baixados = coletar_em_paralelo(urls)

    grupos = {"A": [], "B": [], "C": [], "E": []}
    cabecalhos_novos = []
    indisponiveis = []
    atribuicao = {}

    for tarefa in tarefas:
        url = tarefa["url"]
        resultado = baixados.get(url)
        if resultado is None:
            indisponiveis.append(url)
            log(f"  {tarefa['grupo']} indisponivel: {url}")
            continue
        for cabecalho_fonte, texto in resultado:
            cabecais, _entradas = parse_m3u(texto)
            cabecalhos_novos.extend(cabecais)
        entradas = entradas_de(resultado)
        log(f"  {tarefa['grupo']} {len(entradas)} canais: {url}")
        if tarefa["escrever"]:
            grupos[tarefa["grupo"]].extend(entradas)
        else:
            atribuicao[url] = {url_da_entrada(b) for b in entradas}

    # D - VOD
    entradas_vod = []
    vod_falhou = False
    for pagina in VOD_SOURCES:
        log(f"Pesquisando VOD: {pagina}")
        resultado = coletar_vod(pagina)
        if resultado is None:
            vod_falhou = True
            log("  VOD indisponivel")
        else:
            entradas_vod.extend(resultado)
            log(f"  VOD {len(resultado)} videos reproduziveis")
    if vod_falhou:
        indisponiveis.append("VOD")

    # preservacao dos dados existentes
    obtidos = {
        url_da_entrada(b)
        for grupo in grupos.values()
        for b in grupo
    } | {url_da_entrada(b) for b in entradas_vod}

    preservados = []
    for url, vistas in atribuicao.items():
        log(f"  preservando registros existentes de {url}")
        preservados.extend(
            b for b in entradas_antigas if url_da_entrada(b) in vistas
        )
    if indisponiveis:
        preservados.extend(
            b for b in entradas_antigas if url_da_entrada(b) not in obtidos
        )

    # montagem final (com remocao de duplicatas)
    finais = []
    vistas = set()

    def adicionar(bloco):
        if len(bloco) < 2:
            return
        chave = (nome_da_entrada(bloco), url_da_entrada(bloco))
        if chave in vistas:
            return
        vistas.add(chave)
        finais.append(bloco)

    for grupo in ("A", "B", "C"):
        for bloco in grupos[grupo]:
            adicionar(bloco)
    for bloco in entradas_vod:
        adicionar(bloco)
    for bloco in grupos["E"]:
        adicionar(bloco)
    for bloco in preservados:
        adicionar(bloco)

    cabecalho = cabecalho_final(cabecalhos_novos, cabecalhos_antigos)
    gravar_saida(cabecalho, finais)

    chaves_coletadas = {
        (nome_da_entrada(b), url_da_entrada(b))
        for grupo in grupos.values()
        for b in grupo
    } | {(nome_da_entrada(b), url_da_entrada(b)) for b in entradas_vod}
    preservados_final = sum(
        1 for b in finais if (nome_da_entrada(b), url_da_entrada(b)) not in chaves_coletadas
    )

    log("")
    log(f"Total gravado: {len(finais)} canais")
    log(f"Preservados (fontes indisponiveis ou fora do periodo): {preservados_final}")
    for caminho in ARQUIVOS_SAIDA:
        log(f"  salvo em {caminho}")
    if indisponiveis:
        log("Fontes preservadas (sem atualizacao):")
        for url in indisponiveis:
            log(f"  - {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
