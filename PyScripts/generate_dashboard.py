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
        best_priority = (-1, "")  # (last_ini_idx, assunto) — para priorizar progresso

        for assunto, topics in sorted(tree[disc].items()):
            last_ini_idx = -1
            for i, t in enumerate(topics):
                if t["iniciado"]:
                    last_ini_idx = i
            next_idx = last_ini_idx + 1
            if next_idx < len(topics) and not topics[next_idx]["iniciado"]:
                # Priorizar assuntos onde já há progresso
                priority = (1 if last_ini_idx >= 0 else 0, assunto)
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
            f'<div class="discipline-row">'
            f'<div class="discipline-info">'
            f'<span class="discipline-name">{escape(name)}</span>'
            f'<span class="discipline-stats">{s["iniciado"]}/{s["total"]} · {mpct}%</span>'
            f'</div>'
            f'<div class="discipline-bar-track">'
            f'<div class="discipline-bar-fill" style="width:{mpct}%;background:{color_fg}"></div>'
            f'</div></div>'
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
            iniciar_items.append(
                f'<div class="iniciar-card">'
                f'<div class="iniciar-card-header">'
                f'<span class="iniciar-topic">{escape(t["name"])}</span>'
                f'</div>'
                f'<div class="iniciar-card-meta">'
                f'<span class="materia-tag" style="background:{color_bg};color:{color_fg}">{escape(t["materia"])}</span>'
                f'<span class="iniciar-assunto">{escape(t["assunto"])}</span>'
                f'</div>'
                f'</div>'
            )
        iniciar_html = '<div class="iniciar-grid">' + "\n".join(iniciar_items) + '</div>'

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
  --bg-secondary: #202020;
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

.dashboard {{
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 32px 60px;
}}

/* ── Header ── */
.dash-header {{ margin-bottom: 40px; }}
.dash-header .emoji-title {{
  font-size: 32px; font-weight: 700; letter-spacing: -0.5px;
  display: flex; align-items: center; gap: 12px;
}}
.dash-header .subtitle {{
  color: var(--text-secondary); font-size: 14px; margin-top: 6px;
}}
.dash-header .date-badge {{
  display: inline-flex; align-items: center; gap: 6px;
  margin-top: 14px; padding: 6px 14px;
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: 999px; font-size: 13px; color: var(--text-secondary); font-weight: 500;
}}

.divider {{ height: 1px; background: var(--border-subtle); margin: 32px 0; }}

/* ── Section ── */
.section {{ margin-bottom: 36px; }}
.section-title {{
  font-size: 14px; font-weight: 600; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px;
  display: flex; align-items: center; gap: 8px;
}}

/* ── Iniciar Hoje (hero) ── */
.iniciar-section {{
  background: linear-gradient(135deg, rgba(82,156,202,0.08) 0%, rgba(157,109,215,0.08) 100%);
  border: 1px solid rgba(82,156,202,0.15);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 36px;
}}
.iniciar-section .section-title {{
  color: var(--accent-blue); margin-bottom: 6px;
}}
.iniciar-subtitle {{
  font-size: 12px; color: var(--text-tertiary); margin-bottom: 16px;
}}
.iniciar-grid {{
  display: flex; flex-direction: column; gap: 8px;
}}
.iniciar-card {{
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  transition: all var(--transition);
}}
.iniciar-card:hover {{
  background: rgba(255,255,255,0.07);
  transform: translateX(4px);
  border-color: rgba(82,156,202,0.25);
}}
.iniciar-card-header {{
  display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
}}
.iniciar-topic {{ font-size: 14px; font-weight: 600; }}
.iniciar-card-meta {{
  display: flex; align-items: center; gap: 8px;
}}
.iniciar-assunto {{
  font-size: 11.5px; color: var(--text-tertiary);
}}

/* ── Stats Grid ── */
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}}
.stat-card {{
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg); padding: 20px 18px;
  transition: all var(--transition); position: relative; overflow: hidden;
}}
.stat-card::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0;
  height: 3px; opacity: 0; transition: opacity var(--transition);
}}
.stat-card:hover {{
  background: var(--bg-card-hover); box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}}
.stat-card:hover::before {{ opacity: 1; }}
.stat-card:nth-child(1)::before {{ background: var(--gradient-main); }}
.stat-card:nth-child(2)::before {{ background: var(--gradient-green); }}
.stat-card:nth-child(3)::before {{ background: var(--accent-blue); }}
.stat-card:nth-child(4)::before {{ background: var(--accent-purple); }}
.stat-card:nth-child(5)::before {{ background: var(--accent-green); }}
.stat-card:nth-child(6)::before {{ background: var(--accent-orange); }}

.stat-card .stat-value {{ font-size: 28px; font-weight: 700; letter-spacing: -1px; line-height: 1; }}
.stat-card .stat-label {{
  font-size: 12px; color: var(--text-tertiary); margin-top: 6px;
  font-weight: 500; text-transform: uppercase; letter-spacing: 0.3px;
}}
.stat-card.accent-blue .stat-value {{ color: var(--accent-blue); }}
.stat-card.accent-purple .stat-value {{ color: var(--accent-purple); }}
.stat-card.accent-green .stat-value {{ color: var(--accent-green); }}
.stat-card.accent-orange .stat-value {{ color: var(--accent-orange); }}
.stat-card.accent-red .stat-value {{ color: var(--accent-red); }}
.stat-card.accent-yellow .stat-value {{ color: var(--accent-yellow); }}

/* ── Progress ── */
.progress-section {{
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg); padding: 24px; margin-bottom: 36px;
}}
.progress-header {{
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;
}}
.progress-header .title {{ font-size: 15px; font-weight: 600; }}
.progress-header .pct {{
  font-size: 24px; font-weight: 700;
  background: var(--gradient-green);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}}
.progress-bar-track {{
  width: 100%; height: 10px; background: rgba(255,255,255,0.06);
  border-radius: 999px; overflow: hidden;
}}
.progress-bar-fill {{
  height: 100%; border-radius: 999px; background: var(--gradient-green);
}}
.progress-details {{
  display: flex; justify-content: space-between;
  margin-top: 10px; font-size: 12px; color: var(--text-tertiary);
}}

/* ── Table ── */
.notion-table {{
  width: 100%; border-collapse: separate; border-spacing: 0;
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg); overflow: hidden;
}}
.notion-table thead th {{
  text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600;
  color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.4px;
  border-bottom: 1px solid var(--border-subtle); background: rgba(255,255,255,0.015);
}}
.notion-table tbody tr {{ transition: background var(--transition); }}
.notion-table tbody tr:hover {{ background: var(--bg-card-hover); }}
.notion-table tbody td {{
  padding: 11px 16px; font-size: 13.5px;
  border-bottom: 1px solid var(--border-subtle); color: var(--text-primary);
}}
.notion-table tbody tr:last-child td {{ border-bottom: none; }}
.notion-table .topic-name {{ font-weight: 500; }}
.notion-table .materia-tag {{
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 500;
}}
.notion-table .rev-badge {{
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 600;
}}
.rev-0 {{ background: rgba(212,76,71,0.12); color: var(--accent-red); }}
.rev-1 {{ background: rgba(203,123,62,0.12); color: var(--accent-orange); }}
.rev-2 {{ background: rgba(198,168,56,0.12); color: var(--accent-yellow); }}
.rev-3 {{ background: rgba(77,171,154,0.12); color: var(--accent-green); }}
.rev-4 {{ background: rgba(82,156,202,0.12); color: var(--accent-blue); }}

.table-footer {{
  padding: 10px 16px; font-size: 12px; color: var(--text-tertiary);
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-top: none; border-radius: 0 0 var(--radius-lg) var(--radius-lg); text-align: center;
}}

/* ── Discipline Bars ── */
.discipline-list {{ display: flex; flex-direction: column; gap: 10px; }}
.discipline-row {{
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 14px 18px;
  transition: all var(--transition);
}}
.discipline-row:hover {{ background: var(--bg-card-hover); transform: translateX(4px); }}
.discipline-info {{
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
}}
.discipline-name {{ font-size: 14px; font-weight: 500; }}
.discipline-stats {{ font-size: 12px; color: var(--text-tertiary); }}
.discipline-bar-track {{
  height: 6px; background: rgba(255,255,255,0.06); border-radius: 999px; overflow: hidden;
}}
.discipline-bar-fill {{ height: 100%; border-radius: 999px; }}

/* ── Checks ── */
.check-on {{ color: var(--accent-green); }}
.check-off {{ color: var(--text-tertiary); opacity: 0.4; }}

/* ── Quick Links ── */
.quick-links {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;
}}
.quick-link {{
  display: flex; align-items: center; gap: 10px; padding: 16px 18px;
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg); text-decoration: none; color: var(--text-primary);
  font-size: 14px; font-weight: 500; transition: all var(--transition); cursor: pointer;
}}
.quick-link:hover {{
  background: var(--bg-card-hover); box-shadow: var(--shadow-hover); transform: translateY(-2px);
}}
.quick-link .link-icon {{
  width: 36px; height: 36px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;
}}
.quick-link:nth-child(1) .link-icon {{ background: rgba(82,156,202,0.15); }}
.quick-link:nth-child(2) .link-icon {{ background: rgba(77,171,154,0.15); }}
.quick-link:nth-child(3) .link-icon {{ background: rgba(157,109,215,0.15); }}

/* ── Alert Badge ── */
.alert-count {{
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 22px; height: 22px; padding: 0 7px;
  border-radius: 999px; font-size: 12px; font-weight: 700; margin-left: 8px;
}}
.alert-count.warn {{ background: rgba(212,76,71,0.15); color: var(--accent-red); }}
.alert-count.ok   {{ background: rgba(77,171,154,0.15); color: var(--accent-green); }}

/* ── Empty State ── */
.empty-state {{
  text-align: center; padding: 32px; color: var(--text-secondary); font-size: 14px;
}}
.empty-state .emoji {{ font-size: 32px; margin-bottom: 8px; display: block; }}

/* ── Footer ── */
.dash-footer {{
  text-align: center; padding: 20px 0 0; font-size: 11px; color: var(--text-tertiary);
}}

@media (max-width: 600px) {{
  .dashboard {{ padding: 24px 16px 40px; }}
  .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .dash-header .emoji-title {{ font-size: 24px; }}
}}
</style>
</head>
<body>

<div class="dashboard">

  <header class="dash-header">
    <div class="emoji-title">📚 SmartNote Dashboard</div>
    <div class="subtitle">Painel de controle do seu estudo</div>
    <div class="date-badge">
      <span>📅</span>
      <span>{today_str} — {weekday_str}</span>
    </div>
  </header>

  <div class="iniciar-section">
    <div class="section-title"><span>🎯</span> Tópicos a Iniciar Hoje</div>
    <div class="iniciar-subtitle">Disciplinas de hoje: {disc_hoje_str} · {len(next_topics)} tópico(s) sugerido(s)</div>
    {iniciar_html}
  </div>

  <section class="section">
    <div class="section-title"><span>📊</span> Estatísticas</div>
    <div class="stats-grid">
{stats_html}
    </div>
  </section>

  <div class="progress-section">
    <div class="progress-header">
      <span class="title">🏆 Progresso Geral</span>
      <span class="pct">{pct}%</span>
    </div>
    <div class="progress-bar-track">
      <div class="progress-bar-fill" style="width:{pct}%"></div>
    </div>
    <div class="progress-details">
      <span>{n_ini} de {total} tópicos</span>
      <span>{total - n_ini} restantes</span>
    </div>
  </div>

  <div class="divider"></div>

  <section class="section">
    <div class="section-title">
      <span>🔥</span> Revisões Pendentes
      <span class="alert-count {pend_count_cls}">{len(pendentes)}</span>
    </div>
    {pend_html}
  </section>

  <div class="divider"></div>

  <section class="section">
    <div class="section-title"><span>📚</span> Progresso por Disciplina</div>
    <div class="discipline-list">
{disc_html}
    </div>
  </section>

  <div class="divider"></div>

  <section class="section">
    <div class="section-title"><span>🕐</span> Últimos Estudados</div>
    {rec_html}
  </section>

  <div class="divider"></div>

  <section class="section">
    <div class="section-title"><span>🚀</span> Acesso Rápido</div>
    <div class="quick-links">
      <a class="quick-link" href="obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FRunBook">
        <div class="link-icon">📋</div><span>RunBook</span>
      </a>
      <a class="quick-link" href="obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FRevisao%20Espacada">
        <div class="link-icon">🔄</div><span>Revisão Espaçada</span>
      </a>
      <a class="quick-link" href="obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FDisciplinas">
        <div class="link-icon">📂</div><span>Disciplinas</span>
      </a>
    </div>
  </section>

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
