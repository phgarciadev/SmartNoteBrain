#!/usr/bin/env python3
"""
update_metrics.py — Registra métricas de estudo em metrics.json.

Uso (via Shell Commands do Obsidian):
    python3 PyScripts/update_metrics.py <file_path> <tipo> "<feitas,acertadas>"

Tipos:
    flash_cards_base, flash_cards_vest,
    questoes_abertas_base, questoes_abertas_vest

Exemplo:
    python3 PyScripts/update_metrics.py /path/to/topico.md flash_cards_base "10,8"
"""

import json
import sys
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


def load_metrics() -> list[dict]:
    """Carrega métricas existentes do JSON."""
    if METRICS_FILE.exists():
        try:
            data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, Exception):
            pass
    return []


def save_metrics(metrics: list[dict]):
    """Salva métricas no JSON."""
    METRICS_FILE.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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
    """Converte path absoluto em relativo ao vault."""
    try:
        return str(Path(file_path).relative_to(VAULT_ROOT))
    except ValueError:
        return file_path


def main():
    if len(sys.argv) < 4:
        print("❌ Uso: update_metrics.py <file_path> <tipo> <feitas,acertadas>")
        sys.exit(1)

    file_path = sys.argv[1]
    metric_type = sys.argv[2]
    input_str = sys.argv[3]

    # Validar tipo
    if metric_type not in VALID_TYPES:
        print(f"❌ Tipo inválido: '{metric_type}'")
        print(f"   Tipos válidos: {', '.join(sorted(VALID_TYPES))}")
        sys.exit(1)

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

    # Labels para notificação
    type_labels = {
        "flash_cards_base": "🃏 Flash Cards (Base)",
        "flash_cards_vest": "🃏 Flash Cards (Vest.)",
        "questoes_abertas_base": "📝 Questões Abertas (Base)",
        "questoes_abertas_vest": "📝 Questões Abertas (Vest.)",
    }
    label = type_labels.get(metric_type, metric_type)
    pct = round(acertadas / feitas * 100) if feitas > 0 else 0

    print(f"✅ {label} registrado!")
    print(f"   📊 {acertadas}/{feitas} ({pct}% acerto)")
    print(f"   📅 {date.today().isoformat()}")


if __name__ == "__main__":
    main()
