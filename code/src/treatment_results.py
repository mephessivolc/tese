import pandas as pd

df = pd.read_csv("resultados_tsp_8.csv")

col = df.columns[-1]   # última coluna -> 'tempo de execucao'

# converte os valores numéricos para duração
tempos = pd.to_timedelta(df[col], unit="s")

def human_readable(td):
    total = td.total_seconds()
    horas, resto = divmod(int(total), 3600)
    minutos, segundos = divmod(resto, 60)
    milissegundos = int(round((total - int(total)) * 1000))

    if horas > 0:
        return f"{horas}h {minutos}min {segundos}s"
    elif minutos > 0:
        return f"{minutos}min {segundos}s"
    elif segundos > 0:
        return f"{segundos}s {milissegundos}ms" if milissegundos else f"{segundos}s"
    else:
        return f"{milissegundos}ms"

df["tempo_humanizado"] = tempos.apply(human_readable)

df.to_csv("resultados_tsp_treated.csv", index=False)

print(df[[col, "tempo_humanizado"]])