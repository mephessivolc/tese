import pandas as pd

df = pd.read_csv("resultados_tsp_9.csv")

col = df.columns[-1]   # última coluna -> 'tempo de execucao'

# converte os valores numéricos para duração
tempos = pd.to_timedelta(df[col], unit="s")

def human_readable(td):
    total = td.total_seconds()

    meses, resto = divmod(int(total), 30 * 24 * 3600)
    semanas, resto = divmod(resto, 7 * 24 * 3600)
    dias, resto = divmod(resto, 24 * 3600)
    horas, resto = divmod(resto, 3600)
    minutos, segundos = divmod(resto, 60)

    milissegundos = int(round((total - int(total)) * 1000))

    partes = []

    if meses > 0:
        partes.append(f"{meses}mes" if meses == 1 else f"{meses}meses")
    if semanas > 0:
        partes.append(f"{semanas}sem" if semanas == 1 else f"{semanas}sems")
    if dias > 0:
        partes.append(f"{dias}dia" if dias == 1 else f"{dias}dias")
    if horas > 0:
        partes.append(f"{horas}h")
    if minutos > 0:
        partes.append(f"{minutos}min")
    if segundos > 0:
        partes.append(f"{segundos}s")
    if milissegundos > 0 and total < 60:
        partes.append(f"{milissegundos}ms")

    return " ".join(partes) if partes else "0ms"

df["tempo_humanizado"] = tempos.apply(human_readable)

df[
    [
        "Numero de cidades",
        "Custo classico",
        "Energia quantica",
        "Caminho quantico",
        "tempo_humanizado",
    ]
].to_csv("resultados_tsp_treated.csv", index=False)

print(df[[col, "tempo_humanizado"]])