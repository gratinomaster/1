import requests

url = "https://drive.usercontent.google.com/uc?id=1zFZUuWtu4Vz4zYhcAAFlvTGrq2zdHApm&export=download"
arquivo_destino = "lista1.M3U"

resposta = requests.get(url)
resposta.raise_for_status()

with open(arquivo_destino, "wb") as arquivo:
    arquivo.write(resposta.content)

print("Download concluído com sucesso!")




