import requests

url = "https://drive.usercontent.google.com/u/0/uc?id=1-FfnDKu_NpGSH_r2HTVMRvMZW2-miBbf&export=download"
arquivo_destino = "lista1.M3U"

resposta = requests.get(url)
resposta.raise_for_status()

with open(arquivo_destino, "wb") as arquivo:
    arquivo.write(resposta.content)

print("Download concluído com sucesso!")

