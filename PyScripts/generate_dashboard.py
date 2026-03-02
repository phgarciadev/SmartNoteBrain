#!/usr/bin/env python3
"""
generate_dashboard.py — Gera Dashboard.html a partir dos dados do vault.

Uso:
    python3 PyScripts/generate_dashboard.py

Saída:
    Dashboard.html na raiz do vault (auto-contido, estilo Notion dark).
"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta, date

VAULT_ROOT = Path(__file__).parent.parent
DISCIPLINAS = VAULT_ROOT / "DailyLearning" / "Disciplinas"
OUTPUT = VAULT_ROOT / "Dashboard.html"

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


def build_dashboard_data(pages: list[dict]) -> dict:
    today = date.today()
    total = len(pages)
    iniciados = [p for p in pages if p["iniciado"]]
    r1 = sum(1 for p in iniciados if p["R1"])
    r2 = sum(1 for p in iniciados if p["R2"])
    r3 = sum(1 for p in iniciados if p["R3"])
    r4 = sum(1 for p in iniciados if p["R4"])

    # Revisões pendentes
    pendentes = []
    for p in iniciados:
        prox = calc_proximo(p)
        if not prox:
            continue
        if prox <= today.isoformat():
            rev = sum([p["R1"], p["R2"], p["R3"], p["R4"]])
            pendentes.append({
                "name": p["name"],
                "materia": p["materia"],
                "data": prox,
                "rev": rev,
                "file": p["file"],
            })
    pendentes.sort(key=lambda x: x["data"])

    # Matérias
    materias: dict[str, dict] = {}
    for p in pages:
        m = p["materia"]
        if m not in materias:
            materias[m] = {"total": 0, "iniciado": 0}
        materias[m]["total"] += 1
        if p["iniciado"]:
            materias[m]["iniciado"] += 1
    mat_list = [
        {"name": k, "total": v["total"], "iniciado": v["iniciado"],
         "pct": round(v["iniciado"] / v["total"] * 100) if v["total"] else 0}
        for k, v in sorted(materias.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    # Recentes
    recentes = sorted(
        [p for p in iniciados if p["primeiro_contato"]],
        key=lambda x: x["primeiro_contato"], reverse=True
    )[:8]

    return {
        "generated": today.isoformat(),
        "today_display": today.strftime("%d de %B de %Y"),
        "weekday": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][today.weekday()],
        "total": total,
        "iniciados": len(iniciados),
        "pct": round(len(iniciados) / total * 100) if total else 0,
        "r1": r1, "r2": r2, "r3": r3, "r4": r4,
        "pendentes": pendentes,
        "materias": mat_list,
        "recentes": recentes,
    }


# ── Template HTML ───────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SmartNote Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ── Reset & Base ───────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
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
  --gradient-warm: linear-gradient(135deg, #CB7B3E 0%, #D44C47 100%);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px var(--border-subtle);
  --shadow-hover: 0 4px 16px rgba(0,0,0,0.3), 0 0 0 1px var(--border-card);
  --transition: 200ms cubic-bezier(0.25, 0.1, 0.25, 1);
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
}

/* ── Scrollbar ──────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

/* ── Layout ─────────────────────────────────────── */
.dashboard {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 32px 60px;
}

/* ── Header ─────────────────────────────────────── */
.dash-header {
  margin-bottom: 40px;
  animation: fadeInUp 0.6s ease;
}

.dash-header .emoji-title {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.5px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.dash-header .subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin-top: 6px;
  font-weight: 400;
}

.dash-header .date-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding: 6px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* ── Divider ────────────────────────────────────── */
.divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 32px 0;
}

/* ── Section ────────────────────────────────────── */
.section {
  margin-bottom: 36px;
  animation: fadeInUp 0.6s ease;
  animation-fill-mode: backwards;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title .icon {
  font-size: 16px;
}

/* ── Stats Grid ─────────────────────────────────── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px 18px;
  transition: all var(--transition);
  cursor: default;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  opacity: 0;
  transition: opacity var(--transition);
}

.stat-card:hover {
  background: var(--bg-card-hover);
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.stat-card:hover::before { opacity: 1; }

.stat-card:nth-child(1)::before { background: var(--gradient-main); }
.stat-card:nth-child(2)::before { background: var(--gradient-green); }
.stat-card:nth-child(3)::before { background: var(--accent-blue); }
.stat-card:nth-child(4)::before { background: var(--accent-purple); }
.stat-card:nth-child(5)::before { background: var(--accent-green); }
.stat-card:nth-child(6)::before { background: var(--accent-orange); }

.stat-card .stat-value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
}

.stat-card .stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 6px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.stat-card.accent-blue .stat-value { color: var(--accent-blue); }
.stat-card.accent-purple .stat-value { color: var(--accent-purple); }
.stat-card.accent-green .stat-value { color: var(--accent-green); }
.stat-card.accent-orange .stat-value { color: var(--accent-orange); }
.stat-card.accent-red .stat-value { color: var(--accent-red); }
.stat-card.accent-yellow .stat-value { color: var(--accent-yellow); }

/* ── Progress Bar ───────────────────────────────── */
.progress-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 36px;
  animation: fadeInUp 0.6s ease 0.15s backwards;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.progress-header .title {
  font-size: 15px;
  font-weight: 600;
}

.progress-header .pct {
  font-size: 24px;
  font-weight: 700;
  background: var(--gradient-green);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.progress-bar-track {
  width: 100%;
  height: 10px;
  background: rgba(255,255,255,0.06);
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--gradient-green);
  transition: width 1.2s cubic-bezier(0.25, 0.1, 0.25, 1);
  width: 0%;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ── Table ──────────────────────────────────────── */
.notion-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.notion-table thead th {
  text-align: left;
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(255,255,255,0.015);
}

.notion-table tbody tr {
  transition: background var(--transition);
}

.notion-table tbody tr:hover {
  background: var(--bg-card-hover);
}

.notion-table tbody td {
  padding: 11px 16px;
  font-size: 13.5px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
}

.notion-table tbody tr:last-child td {
  border-bottom: none;
}

.notion-table .topic-name {
  font-weight: 500;
}

.notion-table .materia-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  background: rgba(82,156,202,0.12);
  color: var(--accent-blue);
}

.notion-table .rev-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
}

.rev-0 { background: rgba(212,76,71,0.12); color: var(--accent-red); }
.rev-1 { background: rgba(203,123,62,0.12); color: var(--accent-orange); }
.rev-2 { background: rgba(198,168,56,0.12); color: var(--accent-yellow); }
.rev-3 { background: rgba(77,171,154,0.12); color: var(--accent-green); }
.rev-4 { background: rgba(82,156,202,0.12); color: var(--accent-blue); }

.table-footer {
  padding: 10px 16px;
  font-size: 12px;
  color: var(--text-tertiary);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-top: none;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  text-align: center;
}

/* ── Discipline Bars ────────────────────────────── */
.discipline-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.discipline-row {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  transition: all var(--transition);
}

.discipline-row:hover {
  background: var(--bg-card-hover);
  transform: translateX(4px);
}

.discipline-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.discipline-name {
  font-size: 14px;
  font-weight: 500;
}

.discipline-stats {
  font-size: 12px;
  color: var(--text-tertiary);
}

.discipline-bar-track {
  height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 999px;
  overflow: hidden;
}

.discipline-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 1s cubic-bezier(0.25, 0.1, 0.25, 1);
  width: 0%;
}

.discipline-row:nth-child(8n+1) .discipline-bar-fill { background: var(--accent-blue); }
.discipline-row:nth-child(8n+2) .discipline-bar-fill { background: var(--accent-purple); }
.discipline-row:nth-child(8n+3) .discipline-bar-fill { background: var(--accent-green); }
.discipline-row:nth-child(8n+4) .discipline-bar-fill { background: var(--accent-orange); }
.discipline-row:nth-child(8n+5) .discipline-bar-fill { background: var(--accent-red); }
.discipline-row:nth-child(8n+6) .discipline-bar-fill { background: var(--accent-yellow); }
.discipline-row:nth-child(8n+7) .discipline-bar-fill { background: var(--accent-pink); }
.discipline-row:nth-child(8n+8) .discipline-bar-fill { background: var(--accent-blue); }

/* ── Checkmarks ─────────────────────────────────── */
.check-on { color: var(--accent-green); }
.check-off { color: var(--text-tertiary); opacity: 0.4; }

/* ── Quick Links ────────────────────────────────── */
.quick-links {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.quick-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  text-decoration: none;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition);
  cursor: pointer;
}

.quick-link:hover {
  background: var(--bg-card-hover);
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.quick-link .link-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.quick-link:nth-child(1) .link-icon { background: rgba(82,156,202,0.15); }
.quick-link:nth-child(2) .link-icon { background: rgba(77,171,154,0.15); }
.quick-link:nth-child(3) .link-icon { background: rgba(157,109,215,0.15); }

/* ── Alert Badge ────────────────────────────────── */
.alert-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  margin-left: 8px;
}

.alert-count.warn { background: rgba(212,76,71,0.15); color: var(--accent-red); }
.alert-count.ok   { background: rgba(77,171,154,0.15); color: var(--accent-green); }

/* ── Empty State ────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 14px;
}

.empty-state .emoji { font-size: 32px; margin-bottom: 8px; display: block; }

/* ── Footer ─────────────────────────────────────── */
.dash-footer {
  text-align: center;
  padding: 20px 0 0;
  font-size: 11px;
  color: var(--text-tertiary);
}

/* ── Animations ─────────────────────────────────── */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.anim-delay-1 { animation-delay: 0.1s; }
.anim-delay-2 { animation-delay: 0.2s; }
.anim-delay-3 { animation-delay: 0.3s; }
.anim-delay-4 { animation-delay: 0.4s; }
.anim-delay-5 { animation-delay: 0.5s; }

/* ── Responsive ─────────────────────────────────── */
@media (max-width: 600px) {
  .dashboard { padding: 24px 16px 40px; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .dash-header .emoji-title { font-size: 24px; }
}
</style>
</head>
<body>

<div class="dashboard">

  <!-- HEADER -->
  <header class="dash-header">
    <div class="emoji-title">📚 SmartNote Dashboard</div>
    <div class="subtitle">Painel de controle do seu estudo</div>
    <div class="date-badge">
      <span>📅</span>
      <span id="date-text"></span>
    </div>
  </header>

  <!-- STATS -->
  <section class="section anim-delay-1">
    <div class="section-title"><span class="icon">📊</span> Estatísticas</div>
    <div class="stats-grid" id="stats-grid"></div>
  </section>

  <!-- PROGRESS -->
  <div class="progress-section anim-delay-2">
    <div class="progress-header">
      <span class="title">🏆 Progresso Geral</span>
      <span class="pct" id="progress-pct"></span>
    </div>
    <div class="progress-bar-track">
      <div class="progress-bar-fill" id="progress-fill"></div>
    </div>
    <div class="progress-details">
      <span id="progress-detail-left"></span>
      <span id="progress-detail-right"></span>
    </div>
  </div>

  <div class="divider"></div>

  <!-- PENDENTES -->
  <section class="section anim-delay-3">
    <div class="section-title">
      <span class="icon">🔥</span> Revisões Pendentes
      <span class="alert-count" id="pendentes-count"></span>
    </div>
    <div id="pendentes-container"></div>
  </section>

  <div class="divider"></div>

  <!-- MATERIAS -->
  <section class="section anim-delay-4">
    <div class="section-title"><span class="icon">📚</span> Progresso por Disciplina</div>
    <div class="discipline-list" id="materias-container"></div>
  </section>

  <div class="divider"></div>

  <!-- RECENTES -->
  <section class="section anim-delay-5">
    <div class="section-title"><span class="icon">🕐</span> Últimos Estudados</div>
    <div id="recentes-container"></div>
  </section>

  <div class="divider"></div>

  <!-- QUICK LINKS -->
  <section class="section anim-delay-5">
    <div class="section-title"><span class="icon">🚀</span> Acesso Rápido</div>
    <div class="quick-links">
      <div class="quick-link" onclick="openInObsidian('DailyLearning/RunBook')">
        <div class="link-icon">📋</div>
        <span>RunBook</span>
      </div>
      <div class="quick-link" onclick="openInObsidian('DailyLearning/Revisao Espacada')">
        <div class="link-icon">🔄</div>
        <span>Revisão Espaçada</span>
      </div>
      <div class="quick-link" onclick="openInObsidian('DailyLearning/Disciplinas')">
        <div class="link-icon">📂</div>
        <span>Disciplinas</span>
      </div>
    </div>
  </section>

  <!-- FOOTER -->
  <div class="dash-footer">
    Gerado em <span id="gen-date"></span> · SmartNoteBrain
  </div>

</div>

<script>
// ── Data injected by generate_dashboard.py ─────────────────────────────────
const DATA = __DASHBOARD_DATA__;

// ── Helpers ────────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '-';
  const [y,m,d] = iso.split('-');
  return `${d}/${m}`;
}

function check(val) {
  return val
    ? '<span class="check-on">✅</span>'
    : '<span class="check-off">⬜</span>';
}

function openInObsidian(path) {
  window.location.href = `obsidian://open?vault=SmartNoteBrain&file=${encodeURIComponent(path)}`;
}

function materiaColors(name) {
  const colors = [
    'rgba(82,156,202,0.12)', 'rgba(157,109,215,0.12)', 'rgba(77,171,154,0.12)',
    'rgba(203,123,62,0.12)', 'rgba(200,91,142,0.12)', 'rgba(198,168,56,0.12)'
  ];
  const textColors = [
    'var(--accent-blue)', 'var(--accent-purple)', 'var(--accent-green)',
    'var(--accent-orange)', 'var(--accent-pink)', 'var(--accent-yellow)'
  ];
  let h = 0;
  for (let i = 0; i < name.length; i++) h = ((h << 5) - h + name.charCodeAt(i)) | 0;
  const idx = Math.abs(h) % colors.length;
  return { bg: colors[idx], color: textColors[idx] };
}

// ── Render ─────────────────────────────────────────────────────────────────
function render() {
  // Date
  document.getElementById('date-text').textContent =
    `${DATA.today_display} — ${DATA.weekday}`;
  document.getElementById('gen-date').textContent = DATA.generated;

  // Stats
  const stats = [
    { value: DATA.total, label: 'Total Tópicos', accent: '' },
    { value: DATA.iniciados, label: 'Estudados', accent: 'accent-green' },
    { value: DATA.r1, label: 'Revisão R1', accent: 'accent-blue' },
    { value: DATA.r2, label: 'Revisão R2', accent: 'accent-purple' },
    { value: DATA.r3, label: 'Revisão R3', accent: 'accent-orange' },
    { value: DATA.r4, label: 'Revisão R4', accent: 'accent-yellow' },
  ];
  const statsGrid = document.getElementById('stats-grid');
  stats.forEach(s => {
    const card = document.createElement('div');
    card.className = `stat-card ${s.accent}`;
    card.innerHTML = `
      <div class="stat-value" data-target="${s.value}">0</div>
      <div class="stat-label">${s.label}</div>`;
    statsGrid.appendChild(card);
  });

  // Animated counters
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    const target = parseInt(el.dataset.target);
    const dur = 1000;
    const start = performance.now();
    function step(now) {
      const t = Math.min((now - start) / dur, 1);
      const ease = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(ease * target);
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });

  // Progress
  document.getElementById('progress-pct').textContent = `${DATA.pct}%`;
  document.getElementById('progress-detail-left').textContent =
    `${DATA.iniciados} de ${DATA.total} tópicos`;
  document.getElementById('progress-detail-right').textContent =
    `${DATA.total - DATA.iniciados} restantes`;
  setTimeout(() => {
    document.getElementById('progress-fill').style.width = `${DATA.pct}%`;
  }, 300);

  // Pendentes
  const pendCount = document.getElementById('pendentes-count');
  pendCount.textContent = DATA.pendentes.length;
  pendCount.className = 'alert-count ' + (DATA.pendentes.length > 0 ? 'warn' : 'ok');

  const pendContainer = document.getElementById('pendentes-container');
  if (DATA.pendentes.length === 0) {
    pendContainer.innerHTML = `<div class="empty-state"><span class="emoji">🎉</span>Parabéns! Nenhuma revisão pendente.</div>`;
  } else {
    const showing = DATA.pendentes.slice(0, 10);
    const mColors = {};
    let html = `<table class="notion-table"><thead><tr>
      <th>📖 Tópico</th><th>📚 Matéria</th><th>📅 Data</th><th>🔄 Revisões</th>
    </tr></thead><tbody>`;
    showing.forEach(p => {
      if (!mColors[p.materia]) mColors[p.materia] = materiaColors(p.materia);
      const mc = mColors[p.materia];
      html += `<tr>
        <td class="topic-name">${p.name}</td>
        <td><span class="materia-tag" style="background:${mc.bg};color:${mc.color}">${p.materia}</span></td>
        <td>${formatDate(p.data)}</td>
        <td><span class="rev-badge rev-${p.rev}">${p.rev}/4</span></td>
      </tr>`;
    });
    html += '</tbody></table>';
    if (DATA.pendentes.length > 10) {
      html += `<div class="table-footer">...e mais ${DATA.pendentes.length - 10} tópicos pendentes</div>`;
    }
    pendContainer.innerHTML = html;
  }

  // Materias
  const matContainer = document.getElementById('materias-container');
  DATA.materias.forEach((m, i) => {
    const row = document.createElement('div');
    row.className = 'discipline-row';
    row.innerHTML = `
      <div class="discipline-info">
        <span class="discipline-name">${m.name}</span>
        <span class="discipline-stats">${m.iniciado}/${m.total} · ${m.pct}%</span>
      </div>
      <div class="discipline-bar-track">
        <div class="discipline-bar-fill" data-pct="${m.pct}"></div>
      </div>`;
    matContainer.appendChild(row);
  });
  setTimeout(() => {
    document.querySelectorAll('.discipline-bar-fill[data-pct]').forEach(el => {
      el.style.width = el.dataset.pct + '%';
    });
  }, 400);

  // Recentes
  const recContainer = document.getElementById('recentes-container');
  if (DATA.recentes.length === 0) {
    recContainer.innerHTML = `<div class="empty-state"><span class="emoji">📝</span>Nenhum tópico estudado ainda.</div>`;
  } else {
    let html = `<table class="notion-table"><thead><tr>
      <th>📖 Tópico</th><th>📅 Data</th><th>R1</th><th>R2</th><th>R3</th><th>R4</th>
    </tr></thead><tbody>`;
    DATA.recentes.forEach(p => {
      html += `<tr>
        <td class="topic-name">${p.name}</td>
        <td>${formatDate(p.primeiro_contato)}</td>
        <td>${check(p.R1)}</td><td>${check(p.R2)}</td>
        <td>${check(p.R3)}</td><td>${check(p.R4)}</td>
      </tr>`;
    });
    html += '</tbody></table>';
    recContainer.innerHTML = html;
  }
}

document.addEventListener('DOMContentLoaded', render);
</script>

</body>
</html>
"""

# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("📊 Lendo dados do vault...")
    pages = load_pages()
    print(f"   {len(pages)} tópicos encontrados")

    data = build_dashboard_data(pages)
    print(f"   {data['iniciados']} iniciados ({data['pct']}%)")
    print(f"   {len(data['pendentes'])} revisões pendentes")
    print(f"   {len(data['materias'])} disciplinas")

    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    html = HTML_TEMPLATE.replace("__DASHBOARD_DATA__", data_json)

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"\n✅ Dashboard gerado: {OUTPUT}")
    print("   Abra no navegador ou carregue via plugin no Obsidian.")


if __name__ == "__main__":
    main()
