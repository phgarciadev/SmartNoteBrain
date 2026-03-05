#!/usr/bin/env python3
"""
generate_dashboard.py — Gera Dashboard.html a partir dos dados do vault.

Uso:
    python3 PyScripts/generate_dashboard.py

Saída:
    Dashboard.html na raiz do vault (auto-contido, estilo Notion dark).
    Todo o conteúdo é HTML estático — sem dependência de JavaScript.
"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta, date
from html import escape
from urllib.parse import quote

VAULT_ROOT = Path(__file__).parent.parent
DISCIPLINAS = VAULT_ROOT / "DailyLearning" / "Disciplinas"
OUTPUT = VAULT_ROOT / "Dashboard.html"

MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
        "Sexta-feira", "Sábado", "Domingo"]

ACCENT_COLORS = [
    ("#529CCA", "rgba(82,156,202,0.12)"),   # blue
    ("#9D6DD7", "rgba(157,109,215,0.12)"),   # purple
    ("#4DAB9A", "rgba(77,171,154,0.12)"),    # green
    ("#CB7B3E", "rgba(203,123,62,0.12)"),    # orange
    ("#D44C47", "rgba(212,76,71,0.12)"),     # red
    ("#C6A838", "rgba(198,168,56,0.12)"),    # yellow
    ("#C85B8E", "rgba(200,91,142,0.12)"),    # pink
]

# Cronograma semanal: weekday index (0=Mon) → lista de disciplinas do dia
CRONOGRAMA = {
    0: ["Matemática", "Língua Portuguesa", "Física", "Literatura"],       # Segunda
    1: ["Química", "História", "Biologia", "Geografia"],                  # Terça
    2: ["Filosofia", "Matemática", "Sociologia", "Química"],              # Quarta
    3: ["Física", "Atualidades", "Biologia", "Geografia"],                # Quinta
    4: ["Matemática", "Artes", "História", "Língua Portuguesa"],          # Sexta
    5: ["Física", "Educação Fisica", "Química", "Biologia"],              # Sábado
    6: ["Sociologia", "Filosofia"],                                       # Domingo
}


def find_next_topics(pages: list[dict], today_weekday: int) -> list[dict]:
    """Para cada disciplina do dia, encontra o próximo tópico não iniciado
    em cada assunto (o primeiro não-iniciado após o último iniciado)."""
    disciplinas_hoje = CRONOGRAMA.get(today_weekday, [])
    # Unique, mantendo ordem
    disc_unique = list(dict.fromkeys(disciplinas_hoje))

    # Agrupar páginas: materia → assunto → lista de páginas (já ordenadas pelo rglob)
    from collections import defaultdict
    tree: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for p in pages:
        tree[p["materia"]][p["assunto"]].append(p)

    results = []
    for disc in disc_unique:
        if disc not in tree:
            continue
        # Encontrar o assunto com progresso mais recente (último iniciado)
        # e pegar o próximo tópico não-iniciado nesse assunto
        best_candidate = None
        best_priority = (-1, "")  # (has_started, max_date) — para priorizar progresso recente

        for assunto, topics in sorted(tree[disc].items()):
            last_ini_idx = -1
            max_date = ""
            for i, t in enumerate(topics):
                if t["iniciado"]:
                    last_ini_idx = i
                    if t.get("primeiro_contato"):
                        max_date = max(max_date, t["primeiro_contato"])
                        
            next_idx = last_ini_idx + 1
            if next_idx < len(topics) and not topics[next_idx]["iniciado"]:
                # Priorizar assuntos onde já há progresso, ordenando pelas datas mais recentes
                priority = (1 if last_ini_idx >= 0 else 0, max_date)
                if best_candidate is None or priority > best_priority:
                    best_candidate = topics[next_idx]
                    best_priority = priority

        if best_candidate:
            results.append(best_candidate)
    return results


# ── Leitura dos dados do vault ──────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end < 0:
        return None
    block = text[3:end]
    fm = {}
    for line in block.splitlines():
        m = re.match(r"^(\w[\w_]*):\s*(.+)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.lower() in ("true", "yes"):
                fm[key] = True
            elif val.lower() in ("false", "no"):
                fm[key] = False
            else:
                fm[key] = val
    return fm


def load_pages() -> list[dict]:
    pages = []
    for f in sorted(DISCIPLINAS.rglob("*.md")):
        content = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        if not fm:
            continue
        parts = f.relative_to(DISCIPLINAS).parts
        materia = re.sub(r"^\d+\.\s*", "", parts[0]) if parts else "Outros"
        assunto = re.sub(r"^\d+\.\s*", "", parts[1]) if len(parts) > 1 else ""
        nome = re.sub(r"^\d+\.\s*", "", f.stem)
        pages.append({
            "name": nome,
            "file": str(f.relative_to(VAULT_ROOT)),
            "materia": materia,
            "assunto": assunto,
            "iniciado": bool(fm.get("iniciado")),
            "primeiro_contato": str(fm["primeiro_contato"])[:10] if fm.get("primeiro_contato") else None,
            "R1": bool(fm.get("R1")),
            "R2": bool(fm.get("R2")),
            "R3": bool(fm.get("R3")),
            "R4": bool(fm.get("R4")),
        })
    return pages


def calc_proximo(page: dict) -> str | None:
    pc_str = page.get("primeiro_contato")
    if not pc_str:
        return None
    try:
        pc = datetime.strptime(pc_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    if page["R4"]:
        d = pc + timedelta(days=112)
    elif page["R3"]:
        d = pc + timedelta(days=52)
    elif page["R2"]:
        d = pc + timedelta(days=22)
    elif page["R1"]:
        d = pc + timedelta(days=8)
    else:
        d = pc + timedelta(days=1)
    return d.isoformat()


def materia_color(name: str) -> tuple[str, str]:
    h = 0
    for ch in name:
        h = ((h << 5) - h + ord(ch)) & 0xFFFFFFFF
    return ACCENT_COLORS[h % len(ACCENT_COLORS)]


def obs_link(file_path: str) -> str:
    """Gera URI obsidian://open para um arquivo do vault."""
    # Remove extensão .md para o Obsidian
    path = file_path
    if path.endswith(".md"):
        path = path[:-3]
    return f"obsidian://open?vault=SmartNoteBrain&file={quote(path)}"


def format_date(iso: str) -> str:
    if not iso:
        return "-"
    parts = iso.split("-")
    return f"{parts[2]}/{parts[1]}"


def check_html(val: bool) -> str:
    return '<span class="check-on">✅</span>' if val else '<span class="check-off">⬜</span>'


# ── Geração do HTML estático ────────────────────────────────────────────────

def build_html(pages: list[dict]) -> str:
    today = date.today()
    total = len(pages)
    iniciados = [p for p in pages if p["iniciado"]]
    n_ini = len(iniciados)
    pct = round(n_ini / total * 100) if total else 0
    r1 = sum(1 for p in iniciados if p["R1"])
    r2 = sum(1 for p in iniciados if p["R2"])
    r3 = sum(1 for p in iniciados if p["R3"])
    r4 = sum(1 for p in iniciados if p["R4"])

    today_str = f"{today.day:02d} de {MESES[today.month]} de {today.year}"
    weekday_str = DIAS[today.weekday()]

    # ── Tópicos a iniciar hoje ──
    next_topics = find_next_topics(pages, today.weekday())
    disc_hoje = CRONOGRAMA.get(today.weekday(), [])
    disc_hoje_unique = list(dict.fromkeys(disc_hoje))

    # ── Pendentes ──
    pendentes = []
    for p in iniciados:
        prox = calc_proximo(p)
        if prox and prox <= today.isoformat():
            rev = sum([p["R1"], p["R2"], p["R3"], p["R4"]])
            pendentes.append({**p, "proximo": prox, "rev": rev})
    pendentes.sort(key=lambda x: x["proximo"])

    # ── Matérias ──
    materias_dict: dict[str, dict] = {}
    for p in pages:
        m = p["materia"]
        if m not in materias_dict:
            materias_dict[m] = {"total": 0, "iniciado": 0}
        materias_dict[m]["total"] += 1
        if p["iniciado"]:
            materias_dict[m]["iniciado"] += 1
    materias = sorted(materias_dict.items(), key=lambda x: x[1]["total"], reverse=True)

    # ── Recentes ──
    recentes = sorted(
        [p for p in iniciados if p["primeiro_contato"]],
        key=lambda x: x["primeiro_contato"], reverse=True
    )[:8]

    # ── Build stat cards HTML ──
    stats = [
        (str(total), "Total Tópicos", ""),
        (str(n_ini), "Estudados", "accent-green"),
        (str(r1), "Revisão R1", "accent-blue"),
        (str(r2), "Revisão R2", "accent-purple"),
        (str(r3), "Revisão R3", "accent-orange"),
        (str(r4), "Revisão R4", "accent-yellow"),
    ]
    stats_html = "\n".join(
        f'    <div class="stat-card {cls}">'
        f'<div class="stat-value">{val}</div>'
        f'<div class="stat-label">{label}</div></div>'
        for val, label, cls in stats
    )

    # ── Build pendentes table HTML ──
    if not pendentes:
        pend_html = '<div class="empty-state"><span class="emoji">🎉</span>Parabéns! Nenhuma revisão pendente.</div>'
    else:
        rows = []
        for p in pendentes[:10]:
            color_fg, color_bg = materia_color(p["materia"])
            rev = p["rev"]
            rows.append(
                f'<tr>'
                f'<td class="topic-name">{escape(p["name"])}</td>'
                f'<td><span class="materia-tag" style="background:{color_bg};color:{color_fg}">{escape(p["materia"])}</span></td>'
                f'<td>{format_date(p["proximo"])}</td>'
                f'<td><span class="rev-badge rev-{rev}">{rev}/4</span></td>'
                f'</tr>'
            )
        pend_html = (
            '<table class="notion-table"><thead><tr>'
            '<th>📖 Tópico</th><th>📚 Matéria</th><th>📅 Data</th><th>🔄 Revisões</th>'
            '</tr></thead><tbody>'
            + "\n".join(rows)
            + '</tbody></table>'
        )
        if len(pendentes) > 10:
            pend_html += f'<div class="table-footer">...e mais {len(pendentes) - 10} tópicos pendentes</div>'

    pend_count_cls = "warn" if pendentes else "ok"

    # ── Build disciplinas HTML ──
    disc_rows = []
    for i, (name, s) in enumerate(materias):
        mpct = round(s["iniciado"] / s["total"] * 100) if s["total"] else 0
        color_fg = ACCENT_COLORS[i % len(ACCENT_COLORS)][0]
        disc_rows.append(
            f'<div class="disc-row">'
            f'<span class="disc-name">{escape(name)}</span>'
            f'<div class="disc-bar-track">'
            f'<div class="disc-bar-fill" style="width:{mpct}%;background:{color_fg}"></div>'
            f'</div>'
            f'<span class="disc-pct">{s["iniciado"]}/{s["total"]}</span>'
            f'</div>'
        )
    disc_html = "\n".join(disc_rows)

    # ── Build recentes table HTML ──
    if not recentes:
        rec_html = '<div class="empty-state"><span class="emoji">📝</span>Nenhum tópico estudado ainda.</div>'
    else:
        rec_rows = []
        for p in recentes:
            rec_rows.append(
                f'<tr>'
                f'<td class="topic-name">{escape(p["name"])}</td>'
                f'<td>{format_date(p["primeiro_contato"])}</td>'
                f'<td>{check_html(p["R1"])}</td><td>{check_html(p["R2"])}</td>'
                f'<td>{check_html(p["R3"])}</td><td>{check_html(p["R4"])}</td>'
                f'</tr>'
            )
        rec_html = (
            '<table class="notion-table"><thead><tr>'
            '<th>📖 Tópico</th><th>📅 Data</th><th>R1</th><th>R2</th><th>R3</th><th>R4</th>'
            '</tr></thead><tbody>'
            + "\n".join(rec_rows)
            + '</tbody></table>'
        )

    # ── Build tópicos a iniciar HTML ──
    if not next_topics:
        iniciar_html = '<div class="empty-state"><span class="emoji">✨</span>Nenhum tópico novo programado para hoje.</div>'
    else:
        iniciar_items = []
        for t in next_topics:
            color_fg, color_bg = materia_color(t["materia"])
            link = obs_link(t["file"])
            iniciar_items.append(
                f'<a class="iniciar-card" href="{link}">'
                f'<div class="iniciar-left">'
                f'<span class="iniciar-topic">{escape(t["name"])}</span>'
                f'<div class="iniciar-card-meta">'
                f'<span class="materia-tag" style="background:{color_bg};color:{color_fg}">{escape(t["materia"])}</span>'
                f'<span class="iniciar-assunto">{escape(t["assunto"])}</span>'
                f'</div>'
                f'</div>'
                f'<span class="iniciar-arrow">→</span>'
                f'</a>'
            )
        iniciar_html = '<div class="iniciar-grid">' + "\n".join(iniciar_items) + '</div>'

    # ── Build cronograma HTML ──
    crono_days = [
        ("Seg", 0), ("Ter", 1), ("Qua", 2), ("Qui", 3),
        ("Sex", 4), ("Sáb", 5), ("Dom", 6),
    ]
    crono_rows = []
    for label, wd in crono_days:
        is_today = (wd == today.weekday())
        cls = "crono-day today" if is_today else "crono-day"
        discs = CRONOGRAMA.get(wd, [])
        pills = []
        for d in discs:
            cfg, cbg = materia_color(d)
            pills.append(f'<span class="crono-pill" style="background:{cbg};color:{cfg}">{escape(d)}</span>')
        crono_rows.append(
            f'<div class="{cls}">'
            f'<div class="crono-label">{label}</div>'
            f'<div class="crono-discs">{" ".join(pills)}</div>'
            f'</div>'
        )
    crono_html = "\n".join(crono_rows)

    disc_hoje_str = ", ".join(disc_hoje_unique) if disc_hoje_unique else "—"

    # ── Final HTML ──
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SmartNote Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg-primary: #191919;
  --bg-card: rgba(255,255,255,0.03);
  --bg-card-hover: rgba(255,255,255,0.055);
  --border-subtle: rgba(255,255,255,0.06);
  --border-card: rgba(255,255,255,0.08);
  --text-primary: #ebebeb;
  --text-secondary: rgba(255,255,255,0.55);
  --text-tertiary: rgba(255,255,255,0.35);
  --accent-blue: #529CCA;
  --accent-purple: #9D6DD7;
  --accent-green: #4DAB9A;
  --accent-orange: #CB7B3E;
  --accent-red: #D44C47;
  --accent-yellow: #C6A838;
  --accent-pink: #C85B8E;
  --gradient-main: linear-gradient(135deg, #529CCA 0%, #9D6DD7 100%);
  --gradient-green: linear-gradient(135deg, #4DAB9A 0%, #529CCA 100%);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --shadow-hover: 0 4px 16px rgba(0,0,0,0.3), 0 0 0 1px var(--border-card);
  --transition: 200ms cubic-bezier(0.25, 0.1, 0.25, 1);
}}

body {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}

::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 3px; }}

/* ── Dashboard Shell ── */
.dashboard {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 28px 48px;
}}

/* ── Header ── */
.dash-header {{
  margin-bottom: 28px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
}}
.header-left {{}}
.dash-header .emoji-title {{
  font-size: 28px; font-weight: 700; letter-spacing: -0.5px;
}}
.dash-header .subtitle {{
  color: var(--text-secondary); font-size: 13px; margin-top: 4px;
}}
.dash-header .date-badge {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px;
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: 999px; font-size: 12px; color: var(--text-secondary); font-weight: 500;
}}

/* ── Card Base ── */
.card {{
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all var(--transition);
}}
.card:hover {{
  background: var(--bg-card-hover);
}}
.card-title {{
  font-size: 12px; font-weight: 600; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 6px;
}}

/* ── Main Grid ── */
.grid-main {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}}
.grid-full {{ grid-column: 1 / -1; }}
.grid-left {{ grid-column: 1 / 2; }}
.grid-right {{ grid-column: 2 / 3; }}

/* ── Hero: Tópicos a Iniciar ── */
.hero-card {{
  background: linear-gradient(135deg, rgba(82,156,202,0.06) 0%, rgba(157,109,215,0.06) 100%);
  border-color: rgba(82,156,202,0.12);
}}
.hero-card .card-title {{ color: var(--accent-blue); }}
.hero-subtitle {{
  font-size: 11px; color: var(--text-tertiary); margin: -8px 0 14px; font-weight: 400;
}}
.iniciar-grid {{ display: flex; flex-direction: column; gap: 6px; }}
.iniciar-card {{
  display: flex; align-items: center; justify-content: space-between;
  text-decoration: none; color: var(--text-primary);
  padding: 10px 14px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: var(--radius-md);
  transition: all var(--transition); cursor: pointer;
}}
.iniciar-card:hover {{
  background: rgba(255,255,255,0.06);
  border-color: rgba(82,156,202,0.2);
  transform: translateX(3px);
}}
.iniciar-left {{ display: flex; flex-direction: column; gap: 3px; }}
.iniciar-topic {{ font-size: 13px; font-weight: 600; }}
.iniciar-card-meta {{ display: flex; align-items: center; gap: 6px; }}
.iniciar-assunto {{ font-size: 10.5px; color: var(--text-tertiary); }}
.iniciar-arrow {{
  font-size: 14px; color: var(--text-tertiary); transition: all var(--transition); flex-shrink: 0;
}}
.iniciar-card:hover .iniciar-arrow {{ color: var(--accent-blue); transform: translateX(3px); }}

/* ── Stats Mini ── */
.stats-row {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}}
.stat-mini {{
  text-align: center;
  padding: 14px 8px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: var(--radius-md);
}}
.stat-mini .val {{
  font-size: 22px; font-weight: 700; letter-spacing: -1px; line-height: 1;
}}
.stat-mini .lbl {{
  font-size: 10px; color: var(--text-tertiary); margin-top: 4px;
  text-transform: uppercase; letter-spacing: 0.3px; font-weight: 500;
}}
.c-blue {{ color: var(--accent-blue); }}
.c-green {{ color: var(--accent-green); }}
.c-purple {{ color: var(--accent-purple); }}
.c-orange {{ color: var(--accent-orange); }}
.c-yellow {{ color: var(--accent-yellow); }}

/* ── Progress ── */
.progress-block {{ margin-top: 4px; }}
.progress-header {{
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
}}
.progress-header .title {{ font-size: 13px; font-weight: 600; }}
.progress-header .pct {{
  font-size: 20px; font-weight: 700;
  background: var(--gradient-green);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}}
.progress-bar-track {{
  width: 100%; height: 8px; background: rgba(255,255,255,0.06);
  border-radius: 999px; overflow: hidden;
}}
.progress-bar-fill {{
  height: 100%; border-radius: 999px; background: var(--gradient-green);
}}
.progress-details {{
  display: flex; justify-content: space-between;
  margin-top: 8px; font-size: 11px; color: var(--text-tertiary);
}}

/* ── Table ── */
.notion-table {{
  width: 100%; border-collapse: separate; border-spacing: 0;
  overflow: hidden;
}}
.notion-table thead th {{
  text-align: left; padding: 8px 12px; font-size: 10.5px; font-weight: 600;
  color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.4px;
  border-bottom: 1px solid var(--border-subtle);
}}
.notion-table tbody tr {{ transition: background var(--transition); }}
.notion-table tbody tr:hover {{ background: rgba(255,255,255,0.03); }}
.notion-table tbody td {{
  padding: 8px 12px; font-size: 12.5px;
  border-bottom: 1px solid rgba(255,255,255,0.03); color: var(--text-primary);
}}
.notion-table tbody tr:last-child td {{ border-bottom: none; }}
.topic-name {{ font-weight: 500; }}
.materia-tag {{
  display: inline-block; padding: 1px 8px; border-radius: 999px;
  font-size: 10.5px; font-weight: 500;
}}
.rev-badge {{
  display: inline-flex; align-items: center; gap: 3px;
  padding: 1px 8px; border-radius: 999px; font-size: 10.5px; font-weight: 600;
}}
.rev-0 {{ background: rgba(212,76,71,0.12); color: var(--accent-red); }}
.rev-1 {{ background: rgba(203,123,62,0.12); color: var(--accent-orange); }}
.rev-2 {{ background: rgba(198,168,56,0.12); color: var(--accent-yellow); }}
.rev-3 {{ background: rgba(77,171,154,0.12); color: var(--accent-green); }}
.rev-4 {{ background: rgba(82,156,202,0.12); color: var(--accent-blue); }}
.table-footer {{
  padding: 8px 12px; font-size: 11px; color: var(--text-tertiary); text-align: center;
  border-top: 1px solid rgba(255,255,255,0.03);
}}

/* ── Discipline Bars ── */
.disc-list {{ display: flex; flex-direction: column; gap: 8px; }}
.disc-row {{
  display: flex; align-items: center; gap: 12px;
  padding: 8px 0;
}}
.disc-name {{ font-size: 12.5px; font-weight: 500; min-width: 120px; }}
.disc-bar-track {{
  flex: 1; height: 6px; background: rgba(255,255,255,0.06);
  border-radius: 999px; overflow: hidden;
}}
.disc-bar-fill {{ height: 100%; border-radius: 999px; }}
.disc-pct {{
  font-size: 11px; color: var(--text-tertiary); min-width: 36px; text-align: right;
}}

/* ── Cronograma ── */
.crono-grid {{ display: flex; flex-direction: column; gap: 5px; }}
.crono-day {{
  display: flex; align-items: center; gap: 10px;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  transition: all var(--transition);
}}
.crono-day:hover {{ background: rgba(255,255,255,0.03); }}
.crono-day.today {{
  background: rgba(82,156,202,0.06);
  border-radius: var(--radius-md);
}}
.crono-label {{
  font-size: 11px; font-weight: 700; min-width: 30px;
  color: var(--text-tertiary);
}}
.crono-day.today .crono-label {{ color: var(--accent-blue); }}
.crono-discs {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.crono-pill {{
  padding: 1px 8px; border-radius: 999px;
  font-size: 10px; font-weight: 500;
}}

/* ── Checks ── */
.check-on {{ color: var(--accent-green); }}
.check-off {{ color: var(--text-tertiary); opacity: 0.4; }}

/* ── Quick Links ── */
.qlinks {{ display: flex; flex-direction: column; gap: 8px; }}
.qlink {{
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  border-radius: var(--radius-md); text-decoration: none; color: var(--text-primary);
  font-size: 13px; font-weight: 500; transition: all var(--transition); cursor: pointer;
}}
.qlink:hover {{
  background: rgba(255,255,255,0.05); transform: translateX(3px);
}}
.qlink-icon {{
  width: 30px; height: 30px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0;
}}

/* ── Alert Badge ── */
.alert-count {{
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px; padding: 0 5px;
  border-radius: 999px; font-size: 10px; font-weight: 700; margin-left: 6px;
}}
.alert-count.warn {{ background: rgba(212,76,71,0.15); color: var(--accent-red); }}
.alert-count.ok   {{ background: rgba(77,171,154,0.15); color: var(--accent-green); }}

/* ── Empty State ── */
.empty-state {{
  text-align: center; padding: 20px; color: var(--text-secondary); font-size: 13px;
}}
.empty-state .emoji {{ font-size: 24px; margin-bottom: 6px; display: block; }}

/* ── Footer ── */
.dash-footer {{
  text-align: center; padding: 24px 0 0; font-size: 10px; color: var(--text-tertiary);
}}

/* ── Responsive ── */
@media (max-width: 700px) {{
  .grid-main {{ grid-template-columns: 1fr; }}
  .grid-left, .grid-right {{ grid-column: 1 / -1; }}
  .dashboard {{ padding: 20px 14px 36px; }}
  .dash-header .emoji-title {{ font-size: 22px; }}
  .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* ── Refresh Button ── */
.refresh-btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition);
  text-decoration: none;
  margin-left: auto;
}}
.refresh-btn:hover {{
  background: rgba(82, 156, 202, 0.1);
  border-color: rgba(82, 156, 202, 0.3);
  color: var(--accent-blue);
}}
.refresh-btn.spinning svg {{
  animation: spin 1s linear infinite;
}}
@keyframes spin {{
  from {{ transform: rotate(0deg); }}
  to {{ transform: rotate(360deg); }}
}}
.refresh-btn svg {{
  width: 14px;
  height: 14px;
}}
</style>
</head>
<body>

<div class="dashboard">

  <!-- HEADER -->
  <header class="dash-header">
    <div class="header-left">
      <div class="emoji-title">📚 SmartNote Dashboard</div>
      <div class="subtitle">Painel de controle do seu estudo</div>
    </div>
    <div class="date-badge">
      <span>📅</span> {today_str} — {weekday_str}
    </div>
  </header>

  <!-- MAIN GRID -->
  <div class="grid-main">

    <!-- ═══ ROW 1: Hero + Stats ═══ -->

    <!-- Tópicos a Iniciar (left) -->
    <div class="card hero-card grid-left">
      <div class="card-title">
        <span>🎯</span> Tópicos a Iniciar Hoje
        <a href="obsidian://shell-commands/?vault=SmartNoteBrain&execute=generate_dashboard" class="refresh-btn" onclick="this.classList.add('spinning'); let initialHTML = document.documentElement.outerHTML; let interval = setInterval(() => {{ fetch(window.location.href, {{cache: 'no-store'}}).then(r => r.text()).then(newHTML => {{ if (newHTML !== initialHTML && newHTML.trim().length > 0) {{ clearInterval(interval); window.location.href = 'obsidian://open?vault=SmartNoteBrain&file=Dashboard.html'; }} }}) }}, 2000);" title="Atualizar Dashboard">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
        </a>
      </div>
      <div class="hero-subtitle">Disciplinas: {disc_hoje_str}</div>
      {iniciar_html}
    </div>

    <!-- Stats + Progress (right) -->
    <div class="card grid-right" style="display:flex;flex-direction:column;justify-content:space-between;">
      <div>
        <div class="card-title"><span>📊</span> Estatísticas</div>
        <div class="stats-row">
          <div class="stat-mini"><div class="val">{total}</div><div class="lbl">Total</div></div>
          <div class="stat-mini"><div class="val c-green">{n_ini}</div><div class="lbl">Estudados</div></div>
          <div class="stat-mini"><div class="val c-blue">{r1}</div><div class="lbl">R1</div></div>
          <div class="stat-mini"><div class="val c-purple">{r2}</div><div class="lbl">R2</div></div>
          <div class="stat-mini"><div class="val c-orange">{r3}</div><div class="lbl">R3</div></div>
          <div class="stat-mini"><div class="val c-yellow">{r4}</div><div class="lbl">R4</div></div>
        </div>
      </div>
      <div class="progress-block">
        <div class="progress-header">
          <span class="title">🏆 Progresso</span>
          <span class="pct">{pct}%</span>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill" style="width:{pct}%"></div>
        </div>
        <div class="progress-details">
          <span>{n_ini}/{total} tópicos</span>
          <span>{total - n_ini} restantes</span>
        </div>
      </div>
    </div>

    <!-- ═══ ROW 2: Revisões + Cronograma ═══ -->

    <!-- Revisões Pendentes (left, wider) -->
    <div class="card grid-left">
      <div class="card-title">
        <span>🔥</span> Revisões Pendentes
        <span class="alert-count {pend_count_cls}">{len(pendentes)}</span>
      </div>
      {pend_html}
    </div>

    <!-- Cronograma (right) -->
    <div class="card grid-right">
      <div class="card-title"><span>🗓️</span> Cronograma Semanal</div>
      <div class="crono-grid">
{crono_html}
      </div>
    </div>

    <!-- ═══ ROW 3: Disciplinas + Recentes ═══ -->

    <!-- Progresso por Disciplina (left) -->
    <div class="card grid-left">
      <div class="card-title"><span>📚</span> Progresso por Disciplina</div>
      <div class="disc-list">
{disc_html}
      </div>
    </div>

    <!-- Últimos Estudados + Quick Links (right) -->
    <div class="grid-right" style="display:flex;flex-direction:column;gap:14px;">
      <div class="card">
        <div class="card-title"><span>🕐</span> Últimos Estudados</div>
        {rec_html}
      </div>
      <div class="card">
        <div class="card-title"><span>🚀</span> Acesso Rápido</div>
        <div class="qlinks">
          <a class="qlink" href="obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FRunBook">
            <div class="qlink-icon" style="background:rgba(82,156,202,0.12)">📋</div>RunBook
          </a>
          <a class="qlink" href="obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FRevisao%20Espacada">
            <div class="qlink-icon" style="background:rgba(77,171,154,0.12)">🔄</div>Revisão Espaçada
          </a>
          <a class="qlink" href="obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FDisciplinas">
            <div class="qlink-icon" style="background:rgba(157,109,215,0.12)">📂</div>Disciplinas
          </a>
        </div>
      </div>
    </div>

  </div>

  <div class="dash-footer">
    Gerado em {today.isoformat()} · SmartNoteBrain
  </div>

</div>

</body>
</html>"""


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("📊 Lendo dados do vault...")
    pages = load_pages()
    print(f"   {len(pages)} tópicos encontrados")

    html = build_html(pages)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard gerado: {OUTPUT}")


if __name__ == "__main__":
    main()
