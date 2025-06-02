import requests
import sqlite3
from datetime import datetime

API_KEY = "f66ded36cf3e17a34a3e94f83b58712b"
URL_ATUAL = "https://api.openweathermap.org/data/2.5/weather"
URL_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"

# Pergunta a cidade
nome_cidade = input("\nDigite o nome da cidade desejada: ").strip().title()

# Conecta ao banco
conn = sqlite3.connect("clima_brasil.db")
cursor = conn.cursor()

# Cria a tabela se não existir
cursor.execute("""
CREATE TABLE IF NOT EXISTS clima (
    cidade TEXT,
    data TEXT,
    tipo TEXT,  -- 'atual' ou 'previsao'
    descricao TEXT,
    temperatura REAL
)
""")

# Apaga registros antigos apenas dessa cidade
cursor.execute("DELETE FROM clima WHERE cidade = ?", (nome_cidade,))

# Clima atual
params_atual = {"q": nome_cidade, "appid": API_KEY, "units": "metric", "lang": "pt_br"}
r_atual = requests.get(URL_ATUAL, params=params_atual)

if r_atual.status_code == 200:
    dados = r_atual.json()
    cursor.execute("INSERT INTO clima VALUES (?, ?, ?, ?, ?)", (
        nome_cidade,
        datetime.utcfromtimestamp(dados["dt"]).strftime("%Y-%m-%d"),
        "atual",
        dados["weather"][0]["description"],
        dados["main"]["temp"]
    ))
else:
    print("Erro ao buscar clima atual.")
    conn.close()
    exit()

# Previsão com mín/máx por dia
params_forecast = {"q": nome_cidade, "appid": API_KEY, "units": "metric", "lang": "pt_br"}
r_forecast = requests.get(URL_FORECAST, params=params_forecast)

if r_forecast.status_code == 200:
    dados = r_forecast.json()
    previsao_por_dia = {}

    for item in dados["list"]:
        data_hora = item["dt_txt"]
        data = data_hora.split(" ")[0]
        temp_min = item["main"]["temp_min"]
        temp_max = item["main"]["temp_max"]
        descricao = item["weather"][0]["description"]

        if data not in previsao_por_dia:
            previsao_por_dia[data] = {
                "min": temp_min,
                "max": temp_max,
                "descricao": descricao
            }
        else:
            previsao_por_dia[data]["min"] = min(previsao_por_dia[data]["min"], temp_min)
            previsao_por_dia[data]["max"] = max(previsao_por_dia[data]["max"], temp_max)

    for data, info in previsao_por_dia.items():
        texto_descricao = f"{info['descricao'].capitalize()} - Mín: {info['min']}°C / Máx: {info['max']}°C"
        cursor.execute("INSERT INTO clima VALUES (?, ?, ?, ?, ?)", (
            nome_cidade,
            data,
            "previsao",
            texto_descricao,
            None  # campo temperatura não é usado na previsão diária
        ))
else:
    print("Erro ao buscar previsão do tempo.")

conn.commit()

# Mostrar clima atual
print(f"\n 🌞 Clima atual em {nome_cidade}:")
cursor.execute("SELECT descricao, temperatura FROM clima WHERE cidade = ? AND tipo = 'atual'", (nome_cidade,))
row = cursor.fetchone()
if row:
    print(f"{row[0].capitalize()}, {row[1]}°C")

# Mostrar previsão
print(f"\n 📅 Previsão para os próximos dias em {nome_cidade}:")
cursor.execute("SELECT data, descricao FROM clima WHERE cidade = ? AND tipo = 'previsao' ORDER BY data", (nome_cidade,))
previsoes = cursor.fetchall()

alerta = False

for data, desc in previsoes:
    print(f"{data}: {desc}")
if "chuva forte" in desc.lower():
        alerta = True

if alerta:
    print(f"\n⚠️ ALERTA: Possibilidade de chuva forte em {nome_cidade}!")
    print("Em caso de emergência, procure abrigo e acione a Defesa Civil (telefone 199).")

conn.close()