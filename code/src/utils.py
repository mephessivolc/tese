# utils.py
import sys
from pathlib import Path


class Logger:
    """
    Gerenciador de contexto que duplica a saída do sys.stdout:
    imprime no terminal e grava simultaneamente em um arquivo de log .txt.
    """
    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.terminal = sys.stdout
        self.log_file = None

    def __enter__(self):
        # Garante que o diretório de destino exista
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = open(self.filepath, "w", encoding="utf-8")
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.terminal
        if self.log_file:
            self.log_file.close()

    def write(self, message):
        self.terminal.write(message)
        if self.log_file:
            self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        if self.log_file:
            self.log_file.flush()


def format_timespan(seconds: float) -> str:
    """Converte um intervalo de tempo em segundos para representação humana."""
    if seconds < 0:
        return "0.00 s"
    if seconds < 1.0:
        return f"{seconds * 1000:.1f} ms"
    if seconds < 60.0:
        return f"{seconds:.2f} s"

    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800
    MONTH = 2592000

    secs = float(seconds)

    months, secs = divmod(secs, MONTH)
    weeks, secs = divmod(secs, WEEK)
    days, secs = divmod(secs, DAY)
    hours, secs = divmod(secs, HOUR)
    minutes, secs = divmod(secs, MINUTE)

    parts = []

    if months > 0:
        parts.append(f"{int(months)} Mês{'es' if months > 1 else ''}")
    if weeks > 0:
        parts.append(f"{int(weeks)} sem")
    if days > 0:
        parts.append(f"{int(days)}d")
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    if secs > 0 or not parts:
        parts.append(f"{secs:.1f}s")

    if len(parts) > 2:
        return f"{parts[0]} e {parts[1]}"
    return " ".join(parts)