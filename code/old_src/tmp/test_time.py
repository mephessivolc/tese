import time
import math 

def ref_time(t):
    s = ""
    t = math.ceil(t)
    if t >= 3600:
        h = int(t / 3600)
        s = s + f"{h} horas "
        t = t - h * 3600
    
    if t >= 60 and t <= 3600:
        m = int(t / 60 )
        s = s + f"{m} minutos "
        t = t - m*60 

    if t < 60 and t != 0:
        s = s + f"{t} segundos"

    return s
# Registrar o tempo inicial
inicio = time.perf_counter()

# --- Seu código aqui ---
time.sleep(34)  # Exemplo: pausa de 2 segundos
# ----------------------

# Registrar o tempo final
fim = time.perf_counter()

# Calcular e exibir a diferença
tempo_total = fim - inicio


print(f"Tempo de execução: {ref_time(tempo_total)}")
