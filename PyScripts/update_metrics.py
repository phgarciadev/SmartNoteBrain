#!/usr/bin/env python3
"""
update_metrics.py — Registra métricas de estudo em metrics.json.

Uso (via Shell Commands do Obsidian):
    python3 PyScripts/update_metrics.py <file_path> <tipo>

O script abre um diálogo para o usuário digitar feitas,acertadas.

Tipos:
    flash_cards_base, flash_cards_vest,
    questoes_abertas_base, questoes_abertas_vest
"""

import json
import sys
import subprocess
from datetime import date
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent
METRICS_FILE = VAULT_ROOT / "DailyLearning" / "metrics.json"

VALID_TYPES = {
    "flash_cards_base",
    "flash_cards_vest",
    "questoes_abertas_base",
    "questoes_abertas_vest",
}

TYPE_LABELS = {
    "flash_cards_base": "🃏 Flash Cards (Base)",
    "flash_cards_vest": "🃏 Flash Cards (Vest.)",
    "questoes_abertas_base": "📝 Questões Abertas (Base)",
    "questoes_abertas_vest": "📝 Questões Abertas (Vest.)",
}


def load_metrics() -> list[dict]:
    if METRICS_FILE.exists():
        try:
            data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, Exception):
            pass
    return []


def save_metrics(metrics: list[dict]):
    METRICS_FILE.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ask_input_zenity(metric_type: str) -> str | None:
    """Abre diálogo zenity para o usuário digitar feitas,acertadas."""
    label = TYPE_LABELS.get(metric_type, metric_type)
    try:
        result = subprocess.run(
            [
                "zenity", "--entry",
                "--title", f"📊 {label}",
                "--text", "Feitas, Acertadas (ex: 10,8)",
                "--entry-text", "",
            ],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return None  # Cancelado
        return result.stdout.strip()
    except FileNotFoundError:
        # zenity não disponível, tenta kdialog
        try:
            result = subprocess.run(
                [
                    "kdialog", "--inputbox",
                    f"{label}\nFeitas, Acertadas (ex: 10,8)",
                ],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return None
            return result.stdout.strip()
        except FileNotFoundError:
            print("❌ Nenhum diálogo disponível (zenity/kdialog). Instale zenity.")
            return None
    except subprocess.TimeoutExpired:
        return None


def parse_input(input_str: str) -> tuple[int, int]:
    """Parseia input 'feitas,acertadas' do usuário."""
    input_str = input_str.strip().strip('"').strip("'")
    parts = [p.strip() for p in input_str.split(",")]

    if len(parts) != 2:
        raise ValueError(
            f"Formato inválido: '{input_str}'. Use: feitas,acertadas (ex: 10,8)"
        )

    feitas = int(parts[0])
    acertadas = int(parts[1])

    if feitas < 0 or acertadas < 0:
        raise ValueError("Valores não podem ser negativos.")
    if acertadas > feitas:
        raise ValueError(
            f"Acertadas ({acertadas}) não pode ser maior que feitas ({feitas})."
        )

    return feitas, acertadas


def get_relative_path(file_path: str) -> str:
    try:
        return str(Path(file_path).relative_to(VAULT_ROOT))
    except ValueError:
        return file_path


def main():
    if len(sys.argv) < 3:
        print("❌ Uso: update_metrics.py <file_path> <tipo>")
        sys.exit(1)

    file_path = sys.argv[1]
    metric_type = sys.argv[2]

    if metric_type not in VALID_TYPES:
        print(f"❌ Tipo inválido: '{metric_type}'")
        print(f"   Tipos válidos: {', '.join(sorted(VALID_TYPES))}")
        sys.exit(1)

    # Pedir input via diálogo
    input_str = ask_input_zenity(metric_type)
    if not input_str:
        print("⏭️ Cancelado pelo usuário.")
        sys.exit(0)

    # Parsear input
    try:
        feitas, acertadas = parse_input(input_str)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Criar entrada
    entry = {
        "file": get_relative_path(file_path),
        "type": metric_type,
        "date": date.today().isoformat(),
        "done": feitas,
        "correct": acertadas,
    }

    # Salvar
    metrics = load_metrics()
    metrics.append(entry)
    save_metrics(metrics)

    label = TYPE_LABELS.get(metric_type, metric_type)
    pct = round(acertadas / feitas * 100) if feitas > 0 else 0

    print(f"✅ {label} registrado!")
    print(f"   📊 {acertadas}/{feitas} ({pct}% acerto)")
    print(f"   📅 {date.today().isoformat()}")


if __name__ == "__main__":
    main()
